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
    try:
        gj    = json.loads(geojson_str)
        geom  = gj.get("geometry", gj) if gj.get("type") == "Feature" else gj
        coords = geom["coordinates"][0]
        R = 6371000
        n = len(coords)
        area = 0.0
        for i in range(n):
            j = (i+1) % n
            lon1, lat1 = math.radians(coords[i][0]), math.radians(coords[i][1])
            lon2, lat2 = math.radians(coords[j][0]), math.radians(coords[j][1])
            area += lon1*lat2 - lon2*lat1
        area = abs(area)/2
        lat_mid = math.radians(sum(c[1] for c in coords)/n)
        return round(area * R * R * math.cos(lat_mid) / 10000, 4)
    except Exception:
        return 0.0


def _parse_kml(kml_bytes: bytes):
    import re
    text = kml_bytes.decode("utf-8", errors="ignore")
    matches = re.findall(r"<coordinates>(.*?)</coordinates>", text, re.DOTALL)
    if not matches:
        return None
    coords = []
    for token in matches[0].strip().split():
        p = token.split(",")
        if len(p) >= 2:
            try: coords.append([float(p[0]), float(p[1])])
            except ValueError: pass
    if len(coords) < 3:
        return None
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    return {"type":"Feature","geometry":{"type":"Polygon","coordinates":[coords]},"properties":{}}


def _parse_geojson(raw: bytes):
    try:
        gj = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    t = gj.get("type")
    if t == "FeatureCollection":
        feats = gj.get("features", [])
        gj = feats[0] if feats else None
    if not gj:
        return None
    if t in ("Polygon","MultiPolygon"):
        gj = {"type":"Feature","geometry":gj,"properties":{}}
    return gj if gj.get("type") == "Feature" else None


def _to_kml(t: Talhao) -> str:
    gj    = json.loads(t.geojson)
    geom  = gj.get("geometry", gj) if gj.get("type") == "Feature" else gj
    coord_str = " ".join(f"{c[0]},{c[1]},0" for c in geom["coordinates"][0])
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{t.nome}</name>
    <Placemark>
      <name>{t.nome}</name>
      <description>Cultura: {t.cultura or '-'} | Área: {t.area_ha or 0:.2f} ha</description>
      <Polygon><outerBoundaryIs><LinearRing>
        <coordinates>{coord_str}</coordinates>
      </LinearRing></outerBoundaryIs></Polygon>
    </Placemark>
  </Document>
</kml>"""


# ── Verificação: admin em impersonation OU cliente logado ─────

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
            gj = _parse_kml(raw)
        elif ext in ("geojson","json"):
            gj = _parse_geojson(raw)
        else:
            flash("Formato não suportado. Use KML, KMZ ou GeoJSON.", "error")
            return redirect(url_for("talhoes.importar"))

        if not gj:
            flash("Não foi possível ler o polígono do arquivo.", "error")
            return redirect(url_for("talhoes.importar"))

        gs  = json.dumps(gj)
        t   = Talhao(user_id=user.id, nome=nome, cultura=cultura,
                     geojson=gs, area_ha=_area_ha(gs))
        db.session.add(t)
        db.session.commit()
        flash(f"Talhão '{nome}' importado! ({t.area_ha:.2f} ha)", "success")
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
