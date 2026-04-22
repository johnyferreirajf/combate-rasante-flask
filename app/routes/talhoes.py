"""
talhoes.py — Rotas do módulo de talhões e solicitações.
Prefixo: /talhoes/
"""
from __future__ import annotations
import io, json, math, zipfile
from datetime import datetime, date

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, send_file, abort, session)

from app import db
from app.models.talhao import Talhao, SolicitacaoAplicacao
from app.utils.security import login_required, get_current_user

talhoes_bp = Blueprint("talhoes", __name__, url_prefix="/talhoes")

CULTURAS = ["Soja","Milho","Cana-de-Açúcar","Café","Algodão",
            "Sorgo","Feijão","Arroz","Trigo","Outro"]


# ── Helpers ───────────────────────────────────────────────────

def _area_ha(geojson_str: str) -> float:
    """Calcula área em ha — suporta Polygon e MultiPolygon."""
    def _poly_area(coords):
        R = 6371000
        n = len(coords)
        a = 0.0
        for i in range(n):
            j = (i+1) % n
            a += math.radians(coords[i][0]) * math.radians(coords[j][1])                - math.radians(coords[j][0]) * math.radians(coords[i][1])
        a = abs(a)/2
        lat_mid = math.radians(sum(c[1] for c in coords)/n)
        return a * R * R * math.cos(lat_mid) / 10000

    try:
        gj   = json.loads(geojson_str)
        geom = gj.get("geometry", gj) if gj.get("type") == "Feature" else gj
        t    = geom.get("type","")
        if t == "Polygon":
            return round(_poly_area(geom["coordinates"][0]), 4)
        elif t == "MultiPolygon":
            return round(sum(_poly_area(poly[0]) for poly in geom["coordinates"]), 4)
        return 0.0
    except Exception:
        return 0.0


def _parse_coords(raw_str: str):
    """Converte string de coordenadas KML em lista [[lon,lat], ...]."""
    import re as _re
    coords = []
    for token in raw_str.strip().split():
        p = token.split(",")
        if len(p) >= 2:
            try: coords.append([float(p[0]), float(p[1])])
            except ValueError: pass
    if len(coords) < 3:
        return None
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords


def _parse_kml(kml_bytes: bytes):
    """
    Extrai TODOS os Placemarks do KML.
    Retorna lista de dicts: [{nome, geojson_feature}, ...]
    Suporta Polygon simples e MultiPolygon (vários outerBoundaryIs).
    """
    import re as _re
    text = kml_bytes.decode("utf-8", errors="ignore")

    # Extrair Placemarks individuais
    placemark_blocks = _re.findall(
        r"<Placemark[^>]*>(.*?)</Placemark>", text, _re.DOTALL | _re.IGNORECASE
    )

    # Se não há blocos separados, tentar extrair todas as <coordinates> diretamente
    if not placemark_blocks:
        all_coords = _re.findall(r"<coordinates>(.*?)</coordinates>", text, _re.DOTALL)
        results = []
        for i, raw in enumerate(all_coords):
            coords = _parse_coords(raw)
            if coords:
                results.append({
                    "nome": f"Talhão {i+1}",
                    "geojson": {"type":"Feature",
                                "geometry":{"type":"Polygon","coordinates":[coords]},
                                "properties":{}}
                })
        return results or None

    results = []
    for i, block in enumerate(placemark_blocks):
        # Nome do placemark
        nm = _re.search(r"<name>(.*?)</name>", block, _re.DOTALL | _re.IGNORECASE)
        nome = nm.group(1).strip() if nm else f"Talhão {i+1}"
        # Limpar tags CDATA
        nome = _re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"", nome).strip() or f"Talhão {i+1}"

        # Todos os polígonos dentro deste placemark
        outer_blocks = _re.findall(
            r"<outerBoundaryIs>(.*?)</outerBoundaryIs>", block, _re.DOTALL | _re.IGNORECASE
        )

        if not outer_blocks:
            # Tentar coordenadas diretamente sem outerBoundaryIs
            raw_coords = _re.findall(r"<coordinates>(.*?)</coordinates>", block, _re.DOTALL)
            if raw_coords:
                outer_blocks = raw_coords  # tratar como lista de outer

        if not outer_blocks:
            continue

        polys = []
        for ob in outer_blocks:
            raw = _re.search(r"<coordinates>(.*?)</coordinates>", ob, _re.DOTALL)
            raw_str = raw.group(1) if raw else ob  # se já é coordenadas brutas
            coords = _parse_coords(raw_str)
            if coords:
                polys.append(coords)

        if not polys:
            continue

        if len(polys) == 1:
            geom = {"type": "Polygon", "coordinates": polys}
        else:
            geom = {"type": "MultiPolygon",
                    "coordinates": [[p] for p in polys]}

        results.append({
            "nome": nome,
            "geojson": {"type":"Feature","geometry":geom,"properties":{}}
        })

    return results if results else None


def _parse_geojson(raw: bytes):
    """Retorna lista de dicts [{nome, geojson_feature}, ...] ou None."""
    try:
        gj = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    t = gj.get("type")

    if t == "FeatureCollection":
        results = []
        for i, feat in enumerate(gj.get("features", [])):
            if feat.get("type") != "Feature":
                continue
            geom = feat.get("geometry", {})
            if geom.get("type") not in ("Polygon","MultiPolygon"):
                continue
            nome = (feat.get("properties") or {}).get("name") or                    (feat.get("properties") or {}).get("Name") or                    (feat.get("properties") or {}).get("nome") or                    f"Talhão {i+1}"
            results.append({"nome": str(nome), "geojson": feat})
        return results if results else None

    if t in ("Polygon","MultiPolygon"):
        gj = {"type":"Feature","geometry":gj,"properties":{}}

    if gj.get("type") == "Feature":
        nome = (gj.get("properties") or {}).get("name") or                (gj.get("properties") or {}).get("nome") or "Talhão 1"
        return [{"nome": str(nome), "geojson": gj}]

    return None


def _ring_kml(ring):
    return " ".join(f"{c[0]},{c[1]},0" for c in ring)


def _to_kml(t: Talhao) -> str:
    gj    = json.loads(t.geojson)
    geom  = gj.get("geometry", gj) if gj.get("type") == "Feature" else gj
    gtype = geom.get("type", "")
    desc  = f"Cultura: {t.cultura or '-'} | Area: {t.area_ha or 0:.2f} ha"

    placemarks = []
    if gtype == "Polygon":
        rings = geom["coordinates"]
        inner = "".join(
            f"<innerBoundaryIs><LinearRing><coordinates>{_ring_kml(r)}</coordinates>"
            f"</LinearRing></innerBoundaryIs>" for r in rings[1:]
        )
        placemarks.append(
            f"<Placemark><n>{t.nome}</n><description>{desc}</description>"
            f"<Polygon><outerBoundaryIs><LinearRing>"
            f"<coordinates>{_ring_kml(rings[0])}</coordinates>"
            f"</LinearRing></outerBoundaryIs>{inner}</Polygon></Placemark>"
        )
    elif gtype == "MultiPolygon":
        for i, poly in enumerate(geom["coordinates"]):
            nm = f"{t.nome} ({i+1})" if len(geom["coordinates"]) > 1 else t.nome
            inner = "".join(
                f"<innerBoundaryIs><LinearRing><coordinates>{_ring_kml(r)}</coordinates>"
                f"</LinearRing></innerBoundaryIs>" for r in poly[1:]
            )
            placemarks.append(
                f"<Placemark><n>{nm}</n><description>{desc}</description>"
                f"<Polygon><outerBoundaryIs><LinearRing>"
                f"<coordinates>{_ring_kml(poly[0])}</coordinates>"
                f"</LinearRing></outerBoundaryIs>{inner}</Polygon></Placemark>"
            )

    body = "\n    ".join(placemarks)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        f'  <Document>\n    <n>{t.nome}</n>\n    {body}\n  </Document>\n</kml>'
    )


def _pode_acessar():
    """Retorna True se admin em impersonation ou cliente logado."""
    user = get_current_user()
    return user is not None


# ── Mapa / editor ─────────────────────────────────────────────

@talhoes_bp.route("/mapa")
@login_required
def mapa():
    user    = get_current_user()
    talhoes = Talhao.query.filter_by(user_id=user.id).all()
    talhoes_json = json.dumps([{
        "id":      t.id,
        "nome":    t.nome,
        "cultura": t.cultura or "",
        "area_ha": t.area_ha or 0,
        "cor":     t.cor or "#22c55e",
        "geojson": json.loads(t.geojson),
    } for t in talhoes])
    editar_id = request.args.get("editar", "null")
    return render_template("talhoes/mapa.html",
                           talhoes_json=talhoes_json,
                           editar_id=editar_id,
                           culturas=CULTURAS,
                           current_user=user)


# ── API: salvar ───────────────────────────────────────────────

@talhoes_bp.route("/api/salvar", methods=["POST"])
@login_required
def api_salvar():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    nome    = (data.get("nome") or "").strip()
    geojson = data.get("geojson")
    if not nome:
        return jsonify({"erro": "Informe o nome do talhão"}), 400
    if not geojson:
        return jsonify({"erro": "Polígono inválido"}), 400

    geojson_str = json.dumps(geojson)
    area = _area_ha(geojson_str)

    tid = data.get("id")
    if tid:
        t = Talhao.query.filter_by(id=tid, user_id=user.id).first_or_404()
        t.nome    = nome
        t.cultura = (data.get("cultura") or "").strip()
        t.cor     = (data.get("cor") or "#22c55e").strip()
        t.geojson = geojson_str
        t.area_ha = area
        t.observacoes = (data.get("observacoes") or "").strip()
    else:
        t = Talhao(user_id=user.id, nome=nome,
                   cultura=(data.get("cultura") or "").strip(),
                   cor=(data.get("cor") or "#22c55e").strip(),
                   geojson=geojson_str, area_ha=area,
                   observacoes=(data.get("observacoes") or "").strip())
        db.session.add(t)

    db.session.commit()
    return jsonify({"ok": True, "id": t.id, "area_ha": area})


# ── API: excluir ──────────────────────────────────────────────

@talhoes_bp.route("/api/excluir/<int:tid>", methods=["DELETE"])
@login_required
def api_excluir(tid):
    user = get_current_user()
    t = Talhao.query.filter_by(id=tid, user_id=user.id).first_or_404()
    db.session.delete(t)
    db.session.commit()
    return jsonify({"ok": True})


# ── Importar KML / GeoJSON ────────────────────────────────────

@talhoes_bp.route("/importar", methods=["GET","POST"])
@login_required
def importar():
    user = get_current_user()
    if request.method == "POST":
        arq     = request.files.get("arquivo")
        nome    = (request.form.get("nome") or "").strip()
        cultura = (request.form.get("cultura") or "").strip()
        if not arq or not arq.filename:
            flash("Selecione um arquivo KML ou GeoJSON.", "error")
            return redirect(url_for("talhoes.importar"))

        raw = arq.read()
        ext = arq.filename.rsplit(".", 1)[-1].lower()
        nome = nome or arq.filename.rsplit(".", 1)[0]

        if ext == "kmz":
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                kml_name = next((n for n in z.namelist() if n.endswith(".kml")), None)
                raw = z.read(kml_name) if kml_name else b""
            ext = "kml"

        if ext == "kml":
            features = _parse_kml(raw)
        elif ext in ("geojson","json"):
            features = _parse_geojson(raw)
        else:
            flash("Formato não suportado. Use KML, KMZ ou GeoJSON.", "error")
            return redirect(url_for("talhoes.importar"))

        if not features:
            flash("Não foi possível ler polígonos do arquivo. Verifique o formato.", "error")
            return redirect(url_for("talhoes.importar"))

        # Salvar cada polígono como um talhão separado
        salvos = 0
        area_total = 0.0
        for feat in features:
            # Nome: prioridade ao campo do form (só para 1 talhão), depois ao nome do arquivo
            nome_talhao = nome if (len(features) == 1 and nome) else feat["nome"]
            gs   = json.dumps(feat["geojson"])
            area = _area_ha(gs)
            t    = Talhao(user_id=user.id, nome=nome_talhao,
                          cultura=cultura, geojson=gs, area_ha=area)
            db.session.add(t)
            salvos     += 1
            area_total += area

        db.session.commit()

        if salvos == 1:
            flash(f"Talhão importado com sucesso! ({area_total:.2f} ha)", "success")
        else:
            flash(f"{salvos} talhões importados! Área total: {area_total:.2f} ha", "success")

        return redirect(url_for("talhoes.mapa"))

    return render_template("talhoes/importar.html",
                           culturas=CULTURAS,
                           current_user=user)


# ── Exportar KML ──────────────────────────────────────────────

@talhoes_bp.route("/exportar/<int:tid>.kml")
@login_required
def exportar_kml(tid):
    user = get_current_user()
    t    = Talhao.query.filter_by(id=tid, user_id=user.id).first_or_404()
    buf  = io.BytesIO(_to_kml(t).encode("utf-8"))
    return send_file(buf, mimetype="application/vnd.google-earth.kml+xml",
                     as_attachment=True,
                     download_name=f"{t.nome.replace(' ','_')}.kml")


# ── Exportar GeoJSON ──────────────────────────────────────────

@talhoes_bp.route("/exportar/<int:tid>.geojson")
@login_required
def exportar_geojson(tid):
    user = get_current_user()
    t    = Talhao.query.filter_by(id=tid, user_id=user.id).first_or_404()
    gj   = json.loads(t.geojson)
    gj.setdefault("properties",{}).update(
        {"nome":t.nome,"cultura":t.cultura,"area_ha":t.area_ha})
    buf  = io.BytesIO(json.dumps(gj, ensure_ascii=False, indent=2).encode("utf-8"))
    return send_file(buf, mimetype="application/geo+json",
                     as_attachment=True,
                     download_name=f"{t.nome.replace(' ','_')}.geojson")


# ── Solicitações — lista ──────────────────────────────────────

@talhoes_bp.route("/solicitacoes")
@login_required
def solicitacoes():
    user = get_current_user()
    sols = (SolicitacaoAplicacao.query
            .filter_by(user_id=user.id)
            .order_by(SolicitacaoAplicacao.created_at.desc())
            .all())
    return render_template("talhoes/solicitacoes.html",
                           solicitacoes=sols, current_user=user)


# ── Solicitações — nova ───────────────────────────────────────

@talhoes_bp.route("/solicitar/<int:tid>", methods=["GET","POST"])
@login_required
def solicitar(tid):
    user   = get_current_user()
    talhao = Talhao.query.filter_by(id=tid, user_id=user.id).first_or_404()

    if request.method == "POST":
        cultura = (request.form.get("cultura") or "").strip()
        produto = (request.form.get("produto") or "").strip()
        if not cultura or not produto:
            flash("Informe a cultura e o produto.", "error")
            return redirect(url_for("talhoes.solicitar", tid=tid))

        data_desejada = None
        data_raw = request.form.get("data_desejada") or ""
        if data_raw:
            try: data_desejada = datetime.strptime(data_raw, "%Y-%m-%d").date()
            except ValueError: pass

        s = SolicitacaoAplicacao(
            user_id=user.id, talhao_id=talhao.id,
            cultura=cultura, produto=produto,
            dose=(request.form.get("dose") or "").strip(),
            data_desejada=data_desejada,
            observacoes=(request.form.get("observacoes") or "").strip(),
        )
        db.session.add(s)
        db.session.commit()
        flash("Solicitação enviada! Nossa equipe entrará em contato.", "success")
        return redirect(url_for("talhoes.solicitacoes"))

    return render_template("talhoes/solicitar.html",
                           talhao=talhao, culturas=CULTURAS,
                           today=date.today().isoformat(),
                           current_user=user)


# ── Admin: todas as solicitações ─────────────────────────────

@talhoes_bp.route("/admin/solicitacoes")
@login_required
def admin_solicitacoes():
    user = get_current_user()
    if not user.is_admin:
        abort(403)
    sols = (SolicitacaoAplicacao.query
            .order_by(SolicitacaoAplicacao.created_at.desc())
            .all())
    return render_template("talhoes/admin_solicitacoes.html",
                           solicitacoes=sols, current_user=user)


@talhoes_bp.route("/admin/solicitacoes/<int:sid>/status", methods=["POST"])
@login_required
def admin_atualizar_status(sid):
    user = get_current_user()
    if not user.is_admin:
        abort(403)
    s = SolicitacaoAplicacao.query.get_or_404(sid)
    s.status        = request.form.get("status", s.status)
    s.resposta_admin = (request.form.get("resposta") or "").strip()
    db.session.commit()
    flash("Status atualizado!", "success")
    return redirect(url_for("talhoes.admin_solicitacoes"))
