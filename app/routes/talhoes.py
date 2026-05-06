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


# ── Gerar preview do mapa e fazer upload no Cloudinary ───────

@talhoes_bp.route("/api/mapa-preview/<int:tid>", methods=["GET"])
@login_required
def mapa_preview(tid):
    """Gera imagem do talhão com Pillow e faz upload no Cloudinary."""
    import json as _json, math as _math
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont

    user   = get_current_user()
    talhao = Talhao.query.filter_by(id=tid, user_id=user.id).first_or_404()

    try:
        geo = _json.loads(talhao.geojson) if isinstance(talhao.geojson, str) else talhao.geojson
        geom = geo.get("geometry") or geo
        cor_hex = talhao.cor or "#22c55e"
        nome    = talhao.nome or "Talhão"
        area_ha = talhao.area_ha or 0

        import random as _rnd
        _rnd.seed(42)

        def _simplificar(coords, max_pts=80):
            if len(coords) <= max_pts: return coords
            step = len(coords) / max_pts
            return [coords[int(i*step)] for i in range(max_pts)] + [coords[0]]

        def _coletar_rings(g):
            t = g.get("type","")
            if t == "Polygon": return [g["coordinates"][0]]
            elif t == "MultiPolygon": return [p[0] for p in g["coordinates"]]
            elif t == "GeometryCollection":
                rs=[]
                for gg in g.get("geometries",[]): rs+=_coletar_rings(gg)
                return rs
            return []

        rings = _coletar_rings(geom)
        if not rings:
            return jsonify({"erro": "GeoJSON sem coordenadas"}), 400

        all_pts = [pt for r in rings for pt in r]
        lons = [p[0] for p in all_pts]
        lats = [p[1] for p in all_pts]

        W, H = 1200, 720
        HEADER, FOOTER = 90, 65
        MAP_H = H - HEADER - FOOTER

        margin = 0.18
        lon_min, lon_max = min(lons), max(lons)
        lat_min, lat_max = min(lats), max(lats)
        dlon = (lon_max - lon_min) or 0.001
        dlat = (lat_max - lat_min) or 0.001
        lon_min -= dlon*margin; lon_max += dlon*margin
        lat_min -= dlat*margin; lat_max += dlat*margin

        def geo2px(lon, lat):
            x = (lon - lon_min) / (lon_max - lon_min) * W
            y = HEADER + (1 - (lat - lat_min) / (lat_max - lat_min)) * MAP_H
            return (x, y)

        # Fundo com gradiente de campo agricola
        img = Image.new("RGB", (W, H), "#1a2e0d")
        draw = ImageDraw.Draw(img, "RGBA")

        for i in range(MAP_H):
            t = i / MAP_H
            rv = int(15 + 35*t + _rnd.randint(-2,2))
            gv = int(28 + 18*t + _rnd.randint(-2,2))
            bv = int(8  +  5*t + _rnd.randint(-1,1))
            draw.line([(0, HEADER+i),(W, HEADER+i)], fill=(rv,gv,bv))

        # Texturas de campo
        for i in range(0, MAP_H, _rnd.randint(18,35)):
            alpha = _rnd.randint(8,22)
            color = _rnd.choice([(255,220,100),(80,120,30),(150,100,40),(60,90,20)])
            draw.line([(0, HEADER+i),(W, HEADER+i)], fill=(*color, alpha))

        # Manchas de vegetacao
        for _ in range(10):
            cx2 = _rnd.randint(0,W); cy2 = _rnd.randint(HEADER,H-FOOTER)
            rw = _rnd.randint(60,200); rh = _rnd.randint(30,80)
            col = _rnd.choice([(40,80,15,20),(100,70,20,18),(60,100,25,18)])
            draw.ellipse([cx2-rw,cy2-rh,cx2+rw,cy2+rh], fill=col)

        # Blur suave no fundo
        from PIL.ImageFilter import GaussianBlur
        bg_crop = img.crop((0,HEADER,W,H-FOOTER))
        img.paste(bg_crop.filter(GaussianBlur(radius=2)), (0,HEADER))
        draw = ImageDraw.Draw(img, "RGBA")

        # Cor hex
        ch2 = cor_hex.lstrip("#")
        cr, cg2, cb2 = int(ch2[0:2],16), int(ch2[2:4],16), int(ch2[4:6],16)

        # Desenhar poligonos (sem pontos nos vertices)
        for ring in rings:
            simp = _simplificar(ring, 80)
            pts = [geo2px(c[0],c[1]) for c in simp]
            if len(pts) < 3: continue
            for d in [8,5,3]:
                draw.polygon([(x+d,y+d) for x,y in pts], fill=(0,0,0,35))
            draw.polygon(pts, fill=(cr,cg2,cb2,55))
            draw.line(pts+[pts[0]], fill=(cr,cg2,cb2,240), width=5)
            draw.line(pts+[pts[0]], fill=(255,255,255,100), width=1)

        # Centroide
        avg_lon = sum(lons)/len(lons)
        avg_lat = sum(lats)/len(lats)
        cpx, cpy = geo2px(avg_lon, avg_lat)

        # Fontes
        try:
            fB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
            fM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            fS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
            fXS= ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            fB = fM = fS = fXS = ImageFont.load_default()

        # Label no centroide
        lbl_nome = nome[:28]
        lbl_w = max(len(lbl_nome)*12, 120) + 30
        lx, ly = cpx - lbl_w//2, cpy - 30
        draw.rounded_rectangle([lx-4,ly-4,lx+lbl_w+4,ly+54], radius=8,
                                fill=(0,0,0,155), outline=(cr,cg2,cb2,120), width=2)
        draw.text((lx+8, ly+4),  lbl_nome,            fill=(255,255,255,230), font=fM)
        draw.text((lx+8, ly+28), f"{area_ha:.2f} ha", fill=(cr,cg2,cb2,220), font=fS)

        # HEADER
        draw.rectangle([0,0,W,HEADER], fill=(3,10,5,252))
        draw.rectangle([0,0,W,5], fill=(cr,cg2,cb2))
        draw.rectangle([0,HEADER-1,W,HEADER+1], fill=(cr,cg2,cb2,80))

        draw.text((22,12), "SOLICITACAO DE APLICACAO", fill=(255,255,255,235), font=fB)
        draw.text((22,48), "Combate Rasante   Aviacao Agricola de Precisao", fill=(cr,cg2,cb2,200), font=fS)
        draw.text((W-20,12), "combaterasante.com.br", fill=(255,255,255,100), font=fXS, anchor="ra")
        draw.text((W-20,30), "Aviacao Agricola", fill=(255,255,255,60), font=fXS, anchor="ra")

        # FOOTER
        draw.rectangle([0,H-FOOTER,W,H], fill=(3,10,5,252))
        draw.rectangle([0,H-FOOTER,W,H-FOOTER+1], fill=(cr,cg2,cb2,80))
        draw.rectangle([0,H-4,W,H], fill=(cr,cg2,cb2))

        tw2 = min(len(nome)*11+30, 420)
        draw.rounded_rectangle([14,H-FOOTER+13,14+tw2,H-FOOTER+45], radius=8,
                                fill=(cr,cg2,cb2,35), outline=(cr,cg2,cb2,100), width=2)
        draw.text((34, H-FOOTER+21), nome[:35], fill=(cr,cg2,cb2,235), font=fM)
        draw.text((34+tw2+12, H-FOOTER+21), f"Area: {area_ha:.2f} ha", fill=(255,255,255,175), font=fS)

        from datetime import date as _date
        draw.text((W-20, H-FOOTER+21), _date.today().strftime("%d/%m/%Y"), fill=(255,255,255,80), font=fXS, anchor="ra")

        # Upload Cloudinary
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=90)
        buf.seek(0)

        import cloudinary, cloudinary.uploader
        cloudinary.config(
            cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
            api_key=current_app.config["CLOUDINARY_API_KEY"],
            api_secret=current_app.config["CLOUDINARY_API_SECRET"],
        )
        result = cloudinary.uploader.upload(
            buf.getvalue(),
            folder="combaterasante/talhoes_preview",
            public_id=f"talhao_{tid}_{user.id}",
            overwrite=True,
            resource_type="image",
        )
        return jsonify({"url": result["secure_url"]})

    except Exception as e:
        current_app.logger.error(f"mapa_preview error: {e}")
        return jsonify({"erro": str(e)}), 500


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
