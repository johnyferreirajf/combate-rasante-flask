"""
talhoes.py — Rotas do módulo de talhões e solicitações.
Prefixo: /talhoes/
"""
from __future__ import annotations
import io, json, math, zipfile
from datetime import datetime, date

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, send_file, abort, session, current_app)

from app import db
from app.models.talhao import Talhao, SolicitacaoAplicacao
from app.utils.security import login_required, get_current_user, employee_login_required, get_current_employee
from app.models import User, Employee

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


def _hex_to_kml_color(hex_color: str, alpha_hex: str = "ff") -> str:
    """Converte #RRGGBB para AABBGGRR (formato KML/Google Earth)."""
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r, g, b = h[0:2], h[2:4], h[4:6]
        return f"{alpha_hex}{b}{g}{r}".lower()
    return f"{alpha_hex}ff0000"   # fallback vermelho


def _to_kml(t: Talhao) -> str:
    gj    = json.loads(t.geojson)
    geom  = gj.get("geometry", gj) if gj.get("type") == "Feature" else gj
    gtype = geom.get("type", "")
    desc  = f"Cultura: {t.cultura or '-'} | Area: {t.area_ha or 0:.2f} ha"

    # ── Estilo: contorno na cor do talhão, preenchimento transparente ──
    cor_linha  = _hex_to_kml_color(t.cor or "#22c55e", "ff")   # 100% opaco
    cor_fill   = _hex_to_kml_color(t.cor or "#22c55e", "33")   # ~20% opaco
    style_id   = "estilo_talhao"
    style_block = (
        f'  <Style id="{style_id}">\n'
        f'    <LineStyle><color>{cor_linha}</color><width>2</width></LineStyle>\n'
        f'    <PolyStyle><color>{cor_fill}</color><fill>1</fill><outline>1</outline></PolyStyle>\n'
        f'  </Style>\n'
    )
    style_ref = f'<styleUrl>#{style_id}</styleUrl>'

    def _placemark(nome_pm, coords_outer, rings_inner):
        inner = "".join(
            f"<innerBoundaryIs><LinearRing><coordinates>{_ring_kml(r)}</coordinates>"
            f"</LinearRing></innerBoundaryIs>" for r in rings_inner
        )
        return (
            f"<Placemark>"
            f"<n>{nome_pm}</n>"
            f"<description>{desc}</description>"
            f"{style_ref}"
            f"<Polygon>"
            f"<outerBoundaryIs><LinearRing>"
            f"<coordinates>{_ring_kml(coords_outer)}</coordinates>"
            f"</LinearRing></outerBoundaryIs>"
            f"{inner}"
            f"</Polygon>"
            f"</Placemark>"
        )

    placemarks = []
    if gtype == "Polygon":
        rings = geom["coordinates"]
        placemarks.append(_placemark(t.nome, rings[0], rings[1:]))
    elif gtype == "MultiPolygon":
        total = len(geom["coordinates"])
        for i, poly in enumerate(geom["coordinates"]):
            nm = f"{t.nome} ({i+1})" if total > 1 else t.nome
            placemarks.append(_placemark(nm, poly[0], poly[1:]))

    body = "\n    ".join(placemarks)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        f'  <Document>\n    <n>{t.nome}</n>\n{style_block}    {body}\n  </Document>\n</kml>'
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
        "id":       t.id,
        "nome":     t.nome,
        "cultura":  t.cultura or "",
        "area_ha":  t.area_ha or 0,
        "cor":      t.cor or "#22c55e",
        "geojson":  json.loads(t.geojson),
        "data_voo": t.data_voo.isoformat() if t.data_voo else "",
        "pista_voo":t.pista_voo or "",
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

    # Campos novos
    from datetime import date as _date
    data_voo_raw = (data.get("data_voo") or "").strip()
    try:
        data_voo_val = _date.fromisoformat(data_voo_raw) if data_voo_raw else None
    except ValueError:
        data_voo_val = None
    pista_voo_val = (data.get("pista_voo") or "").strip()

    tid = data.get("id")
    if tid:
        t = Talhao.query.filter_by(id=tid, user_id=user.id).first_or_404()
        t.nome      = nome
        t.cultura   = (data.get("cultura") or "").strip()
        t.cor       = (data.get("cor") or "#22c55e").strip()
        t.geojson   = geojson_str
        t.area_ha   = area
        t.observacoes = (data.get("observacoes") or "").strip()
        t.data_voo  = data_voo_val
        t.pista_voo = pista_voo_val
    else:
        t = Talhao(user_id=user.id, nome=nome,
                   cultura=(data.get("cultura") or "").strip(),
                   cor=(data.get("cor") or "#22c55e").strip(),
                   geojson=geojson_str, area_ha=area,
                   observacoes=(data.get("observacoes") or "").strip(),
                   data_voo=data_voo_val, pista_voo=pista_voo_val)
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

        # ── Agrupar todos os polígonos do arquivo em UMA fazenda ──
        # Cada arquivo importado = 1 entrada na sidebar (fazenda),
        # independente de ter 1 ou N talhões/placemarks dentro.
        # Geometria: Polygon (1 feature) ou MultiPolygon (N features).

        nome_fazenda = nome or arq.filename.rsplit(".", 1)[0]

        if len(features) == 1:
            # Arquivo com um único polígono — salvar como Polygon normal
            geojson_final = features[0]["geojson"]
            # Se o nome do form não foi preenchido, usar o nome do placemark
            if not nome:
                nome_fazenda = features[0]["nome"]
        else:
            # Vários placemarks → fundir em um MultiPolygon
            # Cada feature pode ser Polygon ou MultiPolygon — normalizar tudo
            all_rings = []
            for feat in features:
                geom = feat["geojson"].get("geometry", feat["geojson"])
                gtype = geom.get("type", "")
                if gtype == "Polygon":
                    all_rings.append(geom["coordinates"])
                elif gtype == "MultiPolygon":
                    all_rings.extend(geom["coordinates"])

            geojson_final = {
                "type": "Feature",
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": all_rings
                },
                "properties": {}
            }

        gs         = json.dumps(geojson_final)
        area_total = _area_ha(gs)
        t          = Talhao(user_id=user.id, nome=nome_fazenda,
                            cultura=cultura, geojson=gs, area_ha=area_total)
        db.session.add(t)
        db.session.commit()

        n_poligonos = len(features)
        if n_poligonos == 1:
            flash(f"Fazenda \"{nome_fazenda}\" importada! ({area_total:.2f} ha)", "success")
        else:
            flash(f"Fazenda \"{nome_fazenda}\" importada com {n_poligonos} talhões! "
                  f"Área total: {area_total:.2f} ha", "success")

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


# ── Gerar preview do mapa (Playwright screenshot) ──────────────

@talhoes_bp.route("/api/mapa-preview/<int:tid>", methods=["GET"])
@login_required
def mapa_preview(tid):
    """Gera screenshot do mapa Leaflet com satélite usando Playwright."""
    import json as _json, os as _os, base64 as _b64
    from io import BytesIO

    user   = get_current_user()
    talhao = Talhao.query.filter_by(id=tid, user_id=user.id).first_or_404()

    try:
        geo     = _json.loads(talhao.geojson) if isinstance(talhao.geojson, str) else talhao.geojson
        cor     = talhao.cor or "#22c55e"
        nome    = talhao.nome or "Talhão"
        area_ha = talhao.area_ha or 0

        todos = Talhao.query.filter_by(user_id=user.id).all()
        features = []
        for t in todos:
            try:
                g = _json.loads(t.geojson) if isinstance(t.geojson, str) else t.geojson
                is_main     = (t.id == tid)
                is_exclusao = (t.cor or "").lower() in ["#dc2626","#ef4444","#b91c1c"]
                features.append({
                    "type": "Feature",
                    "geometry": g.get("geometry") or g,
                    "properties": {
                        "nome": t.nome or "",
                        "cor":  t.cor or "#22c55e",
                        "is_main": is_main,
                        "is_exclusao": is_exclusao
                    }
                })
            except Exception:
                pass

        fc_json = _json.dumps({"type":"FeatureCollection","features":features})

        # Logo em base64
        logo_b64 = ""
        logo_path = _os.path.join(current_app.root_path, "static", "img", "logo-combate.jpeg")
        if _os.path.exists(logo_path):
            with open(logo_path, "rb") as lf:
                logo_b64 = "data:image/jpeg;base64," + _b64.b64encode(lf.read()).decode()

        logo_tag = f'<img class="logo" src="{logo_b64}">' if logo_b64 else ""
        today = __import__("datetime").date.today().strftime("%d/%m/%Y")

        html = f"""<!DOCTYPE html><html><head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:#071a0d;font-family:Arial,sans-serif;}}
#map{{width:1200px;height:630px;}}
#header{{width:1200px;height:70px;background:rgba(3,12,5,0.97);display:flex;
         align-items:center;justify-content:space-between;padding:0 20px;
         border-bottom:3px solid {cor};}}
#footer{{width:1200px;height:50px;background:rgba(3,12,5,0.97);display:flex;
         align-items:center;justify-content:space-between;padding:0 20px;
         border-top:2px solid {cor};}}
.htitle{{color:#fff;font-size:22px;font-weight:900;letter-spacing:1px;}}
.hsub{{color:{cor};font-size:13px;margin-top:2px;}}
.logo{{height:52px;border-radius:8px;}}
.nome-pill{{background:{cor}33;border:1.5px solid {cor}88;border-radius:6px;
            padding:4px 14px;color:{cor};font-size:15px;font-weight:800;}}
.finfo{{color:#fff;font-size:13px;font-weight:700;}}
.fleg{{color:rgba(255,255,255,0.65);font-size:11px;display:flex;align-items:center;gap:4px;}}
.fdate{{color:rgba(255,255,255,0.45);font-size:12px;}}
.main-label{{background:rgba(0,0,0,0.80);border:none!important;color:#fff;font-weight:900;
             font-size:13px;padding:3px 8px;border-radius:4px;
             box-shadow:0 2px 6px rgba(0,0,0,0.6);white-space:nowrap;}}
.other-label{{background:rgba(0,0,0,0.55);border:none!important;
              color:rgba(255,255,255,0.8);font-size:11px;
              padding:2px 6px;border-radius:4px;}}
.coord-icon{{background:transparent!important;border:none!important;}}
.coord-pin{{width:10px;height:10px;background:#fff;border:2px solid {cor};
            border-radius:50%;position:absolute;top:22px;left:0;
            box-shadow:0 0 0 3px {cor}55;}}
.coord-text{{position:absolute;top:0;left:14px;
             background:rgba(0,0,0,0.85);border:1px solid rgba(255,255,255,0.25);
             border-radius:6px;padding:4px 9px;white-space:nowrap;
             box-shadow:0 2px 8px rgba(0,0,0,0.7);}}
.coord-lat,.coord-lon{{display:block;font-size:11px;font-weight:700;
                        font-family:monospace;color:#86efac;line-height:1.45;}}
</style>
</head><body>
<div id="header">
  <div>
    <div class="htitle">MAPA DE APLICACAO</div>
    <div class="hsub">Combate Rasante &mdash; Aviacao Agricola de Precisao</div>
  </div>
  {logo_tag}
</div>
<div id="map"></div>
<div id="footer">
  <div style="display:flex;align-items:center;gap:14px;">
    <span class="nome-pill">{nome}</span>
    <span class="finfo">{area_ha:.2f} ha</span>
  </div>
  <div style="display:flex;align-items:center;gap:18px;">
    <span class="fleg"><span style="color:{cor};font-size:14px;">&#9632;</span> Area principal</span>
    <span class="fleg"><span style="color:#dc2626;font-size:14px;">&#9632;</span> Exclusao</span>
    <span class="fleg"><span style="color:rgba(255,255,255,0.35);font-size:14px;">&#9632;</span> Demais areas</span>
    <span class="fdate">{today}</span>
  </div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
var fc = {fc_json};

var map = L.map('map',{{zoomControl:false,attributionControl:false,tap:false,
                         preferCanvas:true}});

var tilesLoaded = 0, tilesTotal = 0;
function checkReady(){{ if(tilesLoaded >= tilesTotal && tilesTotal > 0) window.TILES_READY = true; }}

var sat = L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',
  {{maxNativeZoom:19,maxZoom:20}});
sat.on('tileloadstart', function(){{ tilesTotal++; }});
sat.on('tileload', function(){{ tilesLoaded++; checkReady(); }});
sat.on('tileerror', function(){{ tilesLoaded++; checkReady(); }});
sat.addTo(map);

L.tileLayer(
  'https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{{z}}/{{y}}/{{x}}',
  {{maxNativeZoom:19,maxZoom:20,opacity:0.65}}).addTo(map);

var mainLayer = null;
L.geoJSON(fc,{{
  style: function(f){{
    var p = f.properties;
    if(p.is_main)     return {{color:p.cor,weight:4,fillColor:p.cor,fillOpacity:0.45}};
    if(p.is_exclusao) return {{color:'#dc2626',weight:3,fillColor:'#dc2626',fillOpacity:0.40}};
    return {{color:'rgba(255,255,255,0.55)',weight:1.5,fillColor:p.cor,fillOpacity:0.12}};
  }},
  onEachFeature: function(f,l){{
    var p = f.properties;
    if(p.nome){{
      l.bindTooltip(p.nome,{{permanent:true,direction:'center',
        className:p.is_main?'main-label':'other-label'}});
    }}
    if(p.is_main) mainLayer = l;
  }}
}}).addTo(map);

if(mainLayer){{
  map.fitBounds(mainLayer.getBounds(),{{padding:[60,60]}});
}}else{{
  map.fitBounds(L.geoJSON(fc).getBounds(),{{padding:[20,20]}});
}}

// Centróide com coordenadas DMS
function toDMS(deg,isLat){{
  var d=Math.abs(deg), gr=Math.floor(d);
  var mRaw=(d-gr)*60, mn=Math.floor(mRaw);
  var sg=((mRaw-mn)*60).toFixed(1);
  var dir=isLat?(deg>=0?'N':'S'):(deg>=0?'L':'O');
  return gr+"° "+mn+"' "+sg+'" '+dir;
}}
function calcArea(coords){{
  var a=0;
  for(var i=0;i<coords.length-1;i++)
    a+=coords[i][0]*coords[i+1][1]-coords[i+1][0]*coords[i][1];
  return Math.abs(a/2);
}}
function centroid(coords){{
  var x=0,y=0,n=coords.length-1;
  for(var i=0;i<n;i++){{x+=coords[i][0];y+=coords[i][1];}}
  return [x/n,y/n];
}}

if(mainLayer){{
  var bestA=-1,bestC=null;
  mainLayer.eachLayer(function(sub){{
    if(!sub.getLatLngs) return;
    var lls=sub.getLatLngs();
    var rings=Array.isArray(lls[0])?lls:[lls];
    rings.forEach(function(ring){{
      var coords=ring.map(function(ll){{return[ll.lng,ll.lat];}});
      coords.push(coords[0]);
      var a=calcArea(coords);
      if(a>bestA){{bestA=a;bestC=centroid(coords);}}
    }});
  }});
  if(!bestC){{var ctr=mainLayer.getBounds().getCenter();bestC=[ctr.lng,ctr.lat];}}

  var dmsLat=toDMS(bestC[1],true), dmsLon=toDMS(bestC[0],false);
  var icon=L.divIcon({{
    className:'coord-icon',
    html:'<div style="position:relative;width:180px;height:44px;">'+
         '<div class="coord-pin"></div>'+
         '<div class="coord-text">'+
           '<span class="coord-lat">'+dmsLat+'</span>'+
           '<span class="coord-lon">'+dmsLon+'</span>'+
         '</div></div>',
    iconAnchor:[0,32],iconSize:[180,44]
  }});
  L.marker([bestC[1],bestC[0]],{{icon:icon,interactive:false}}).addTo(map);
}}

window.TILES_READY = false;
setTimeout(function(){{ window.TILES_READY = true; }}, 8000);
</script>
</body></html>"""

        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=[
                "--no-sandbox","--disable-dev-shm-usage",
                "--disable-gpu","--disable-web-security"
            ])
            page = browser.new_page(viewport={{"width":1200,"height":750}})
            page.set_content(html, wait_until="domcontentloaded")
            # Aguardar tiles carregarem (até 10s)
            try:
                page.wait_for_function("window.TILES_READY === true", timeout=10000)
            except Exception:
                page.wait_for_timeout(8000)
            screenshot = page.screenshot(
                clip={{"x":0,"y":0,"width":1200,"height":750}},
                type="jpeg", quality=93
            )
            browser.close()

        import cloudinary, cloudinary.uploader
        cloudinary.config(
            cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
            api_key=current_app.config["CLOUDINARY_API_KEY"],
            api_secret=current_app.config["CLOUDINARY_API_SECRET"],
        )
        result = cloudinary.uploader.upload(
            screenshot,
            folder="combaterasante/talhoes_preview",
            public_id=f"talhao_{tid}_{user.id}",
            overwrite=True,
            resource_type="image",
        )
        return jsonify({{"url": result["secure_url"]}})

    except Exception as e:
        current_app.logger.error(f"mapa_preview error: {e}")
        return jsonify({{"erro": str(e)}}), 500


# ── GIS de Clientes para Funcionários ─────────────────────────

@talhoes_bp.route("/funcionario/clientes")
@employee_login_required
def gis_lista_clientes():
    """Funcionário vê lista de clientes para acessar o GIS."""
    emp = get_current_employee()
    if not emp or not emp.acesso_gis:
        abort(403)
    clientes = User.query.filter_by(is_admin=False).order_by(User.name).all()
    return render_template("talhoes/gis_lista_clientes.html",
                           funcionario=emp, clientes=clientes)


@talhoes_bp.route("/funcionario/mapa/<int:uid>")
@employee_login_required
def gis_mapa_cliente(uid):
    """Funcionário acessa o GIS de um cliente específico."""
    emp = get_current_employee()
    if not emp or not emp.acesso_gis:
        abort(403)
    cliente = User.query.get_or_404(uid)
    talhoes = Talhao.query.filter_by(user_id=uid).all()
    talhoes_json = json.dumps([{
        "id":        t.id,
        "nome":      t.nome or "",
        "cultura":   t.cultura or "",
        "cor":       t.cor or "#22c55e",
        "area_ha":   float(t.area_ha or 0),
        "geojson":   json.loads(t.geojson) if isinstance(t.geojson, str) else t.geojson,
        "data_voo":  t.data_voo.strftime("%d/%m/%Y") if t.data_voo else "",
        "pista_voo": t.pista_voo or "",
        "observacoes": t.observacoes or "",
    } for t in talhoes if t.geojson])
    return render_template("talhoes/mapa.html",
                           talhoes_json=talhoes_json,
                           editar_id=None,
                           culturas=CULTURAS,
                           gis_uid=uid,
                           gis_cliente=cliente,
                           gis_funcionario=emp)


@talhoes_bp.route("/funcionario/api/salvar/<int:uid>", methods=["POST"])
@employee_login_required
def gis_salvar_cliente(uid):
    """Funcionário salva talhão no contexto do cliente."""
    emp = get_current_employee()
    if not emp or not emp.acesso_gis:
        return jsonify({"erro": "Sem permissão"}), 403
    # Reusar a lógica de salvar mas com user_id=uid
    data    = request.get_json(force=True) or {}
    tid     = data.get("id")
    nome    = (data.get("nome") or "").strip() or "Sem nome"
    geojson = data.get("geojson")
    if not geojson:
        return jsonify({"erro": "GeoJSON ausente"}), 400
    gj_str  = json.dumps(geojson)
    area_ha = _area_ha(gj_str)

    from datetime import date as _date2
    def parse_date(s):
        if not s: return None
        for fmt in ["%d/%m/%Y","%Y-%m-%d"]:
            try:
                from datetime import datetime as _dt
                return _dt.strptime(s, fmt).date()
            except: pass
        return None
    if tid:
        t = Talhao.query.filter_by(id=tid, user_id=uid).first_or_404()
        t.nome        = nome
        t.geojson     = gj_str
        t.area_ha     = area_ha
        t.cor         = data.get("cor") or t.cor
        t.cultura     = data.get("cultura") or ""
        t.data_voo    = parse_date(data.get("data_voo"))
        t.pista_voo   = data.get("pista_voo") or ""
        t.observacoes = data.get("observacoes") or ""
    else:
        t = Talhao(user_id=uid, nome=nome, geojson=gj_str, area_ha=area_ha,
                   cor=data.get("cor") or "#22c55e",
                   cultura=data.get("cultura") or "",
                   data_voo=parse_date(data.get("data_voo")),
                   pista_voo=data.get("pista_voo") or "",
                   observacoes=data.get("observacoes") or "")
        db.session.add(t)
    db.session.commit()
    return jsonify({"ok": True, "id": t.id, "area_ha": float(t.area_ha or 0)})


@talhoes_bp.route("/funcionario/api/excluir/<int:uid>/<int:tid>", methods=["DELETE"])
@employee_login_required
def gis_excluir_cliente(uid, tid):
    emp = get_current_employee()
    if not emp or not emp.acesso_gis:
        return jsonify({"erro": "Sem permissão"}), 403
    t = Talhao.query.filter_by(id=tid, user_id=uid).first_or_404()
    db.session.delete(t)
    db.session.commit()
    return jsonify({"ok": True})


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

    # Agrupar por cliente
    from collections import OrderedDict
    grupos = OrderedDict()
    for s in sols:
        uid = s.user_id
        if uid not in grupos:
            grupos[uid] = {"user": s.user, "solicitacoes": []}
        grupos[uid]["solicitacoes"].append(s)

    clientes_list = list(grupos.values())
    # Ordenar: clientes com pendentes primeiro
    clientes_list.sort(
        key=lambda g: any(s.status == "pendente" for s in g["solicitacoes"]),
        reverse=True
    )

    return render_template("talhoes/admin_solicitacoes.html",
                           solicitacoes=sols,
                           clientes=clientes_list,
                           current_user=user)


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
