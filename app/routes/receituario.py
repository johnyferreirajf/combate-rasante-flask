"""Módulo de Receituário Agronômico — Combate Rasante Aviação Agrícola."""
from datetime import datetime, date, timedelta
import requests
import time
import base64
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, session, current_app, Response)
from sqlalchemy import text
from app import db
from app.utils.security import login_required, admin_required, get_current_user, get_current_employee

receituario_bp = Blueprint("receituario", __name__)

# =============================================================================
# CREDENCIAIS DA AGROAPI (EMBRAPA)
# =============================================================================
AGROAPI_KEY = "CEpPWXr0CqatrJPFZJSfBoAxFTka"
AGROAPI_SECRET = "KVYMu619dgmFUSqErSv18OFIIkka"

TOKEN_CACHE = {"access_token": None, "expires_at": 0}

def _get_agroapi_token():
    if TOKEN_CACHE["access_token"] and time.time() < TOKEN_CACHE["expires_at"]:
        return TOKEN_CACHE["access_token"]

    url = "https://api.cnptia.embrapa.br/token"
    credenciais = f"{AGROAPI_KEY}:{AGROAPI_SECRET}"
    credenciais_b64 = base64.b64encode(credenciais.encode('utf-8')).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {credenciais_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        r_json = response.json()
        
        TOKEN_CACHE["access_token"] = r_json["access_token"]
        TOKEN_CACHE["expires_at"] = time.time() + r_json.get("expires_in", 3600) - 60
        return TOKEN_CACHE["access_token"]
    except Exception as e:
        print(f"ERRO DE AUTENTICAÇÃO AGROAPI: {e}")
        return None

def auto_migrate_db():
    """Cria as colunas novas na tabela do Railway para evitar a tela branca ao salvar."""
    try:
        comandos = [
            "ALTER TABLE itens_receituario ADD COLUMN IF NOT EXISTS produto_id_api VARCHAR(100);",
            "ALTER TABLE itens_receituario ADD COLUMN IF NOT EXISTS produto_nome VARCHAR(300);",
            "ALTER TABLE itens_receituario ADD COLUMN IF NOT EXISTS produto_ia VARCHAR(500);",
            "ALTER TABLE itens_receituario ADD COLUMN IF NOT EXISTS produto_classe VARCHAR(100);"
        ]
        for cmd in comandos:
            try:
                db.session.execute(text(cmd.replace(" IF NOT EXISTS", "")))
                db.session.commit()
            except Exception:
                db.session.rollback()
    except Exception:
        pass

def _is_admin():
    emp = get_current_employee()
    return emp and emp.is_admin

def _employee_pode_receituario():
    emp = get_current_employee()
    return emp and getattr(emp, "pode_receituario", False)

def _get_emp():
    return get_current_employee()

@receituario_bp.route("/admin/receituario")
@login_required
@admin_required
def admin_lista():
    from app.models.receituario import Receituario, Cultura
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    cult = request.args.get("cultura", "")

    query = Receituario.query.order_by(Receituario.data_criacao.desc())
    if q:
        query = query.filter(Receituario.nome_produtor.ilike(f"%{q}%") | Receituario.numero.ilike(f"%{q}%"))
    if status:
        query = query.filter_by(status=status)
    if cult:
        query = query.filter_by(cultura_id=int(cult))

    receituarios = query.limit(200).all()
    culturas = Cultura.query.filter_by(ativo=True).order_by(Cultura.nome).all()

    total = Receituario.query.count()
    emitidos = Receituario.query.filter_by(status="emitido").count()
    rascunhos = Receituario.query.filter_by(status="rascunho").count()

    return render_template("receituario_admin.html", current_user=get_current_user(),
                           receituarios=receituarios, culturas=culturas,
                           total=total, emitidos=emitidos, rascunhos=rascunhos,
                           q=q, status_filtro=status, cult_filtro=cult)

@receituario_bp.route("/admin/receituario/novo", methods=["GET", "POST"])
@login_required
@admin_required
def admin_novo():
    from app.models.receituario import Cultura
    from app.models.user import User
    culturas = Cultura.query.filter_by(ativo=True).order_by(Cultura.nome).all()
    clientes = User.query.filter_by(is_admin=False).order_by(User.name).all()

    if request.method == "POST":
        return _salvar_receituario(request.form, None)

    return render_template("receituario_form.html", current_user=get_current_user(),
                           rec=None, culturas=culturas, produtos=[], clientes=clientes, modo="admin")

@receituario_bp.route("/admin/receituario/<int:rid>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def admin_editar(rid):
    from app.models.receituario import Receituario, Cultura
    from app.models.user import User
    rec = Receituario.query.get_or_404(rid)
    culturas = Cultura.query.filter_by(ativo=True).order_by(Cultura.nome).all()
    clientes = User.query.filter_by(is_admin=False).order_by(User.name).all()

    if request.method == "POST":
        return _salvar_receituario(request.form, rec)

    return render_template("receituario_form.html", current_user=get_current_user(),
                           rec=rec, culturas=culturas, produtos=[], clientes=clientes, modo="admin")

@receituario_bp.route("/admin/receituario/<int:rid>")
@login_required
@admin_required
def admin_ver(rid):
    from app.models.receituario import Receituario
    rec = Receituario.query.get_or_404(rid)
    return render_template("receituario_view.html", current_user=get_current_user(), rec=rec, modo="admin")

@receituario_bp.route("/admin/receituario/<int:rid>/emitir", methods=["POST"])
@login_required
@admin_required
def admin_emitir(rid):
    from app.models.receituario import Receituario
    rec = Receituario.query.get_or_404(rid)
    if rec.status_geral_validacao == "NAO":
        flash("Não é possível emitir: há produtos incompatíveis com a cultura.", "error")
        return redirect(url_for("receituario.admin_ver", rid=rid))
    if not rec.itens:
        flash("Adicione ao menos um produto antes de emitir.", "error")
        return redirect(url_for("receituario.admin_ver", rid=rid))
    rec.status = "emitido"
    rec.data_emissao = datetime.utcnow()
    rec.data_validade = date.today() + timedelta(days=90)
    db.session.commit()
    flash(f"Receituário {rec.numero} emitido com sucesso!", "success")
    return redirect(url_for("receituario.admin_ver", rid=rid))

@receituario_bp.route("/admin/receituario/<int:rid>/cancelar", methods=["POST"])
@login_required
@admin_required
def admin_cancelar(rid):
    from app.models.receituario import Receituario
    rec = Receituario.query.get_or_404(rid)
    rec.status = "cancelado"
    db.session.commit()
    flash("Receituário cancelado.", "success")
    return redirect(url_for("receituario.admin_lista"))

@receituario_bp.route("/admin/receituario/<int:rid>/excluir", methods=["POST"])
@login_required
@admin_required
def admin_excluir(rid):
    from app.models.receituario import Receituario
    rec = Receituario.query.get_or_404(rid)
    db.session.delete(rec)
    db.session.commit()
    flash("Receituário excluído.", "success")
    return redirect(url_for("receituario.admin_lista"))

def _func_login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        emp = _get_emp()
        if not emp:
            return redirect(url_for("employee.login"))
        if not getattr(emp, "pode_receituario", False) and not emp.is_admin:
            flash("Você não tem permissão para acessar o Receituário Agronômico.", "error")
            return redirect(url_for("employee.index"))
        return f(*args, **kwargs)
    return decorated

@receituario_bp.route("/func/receituario")
@_func_login_required
def func_lista():
    from app.models.receituario import Receituario
    emp = _get_emp()
    recs = (Receituario.query.filter_by(criado_por_func=emp.id).order_by(Receituario.data_criacao.desc()).limit(100).all())
    return render_template("receituario_func_lista.html", current_employee=emp, receituarios=recs)

@receituario_bp.route("/func/receituario/novo", methods=["GET", "POST"])
@_func_login_required
def func_novo():
    from app.models.receituario import Cultura
    emp = _get_emp()
    culturas = Cultura.query.filter_by(ativo=True).order_by(Cultura.nome).all()

    if request.method == "POST":
        return _salvar_receituario(request.form, None, func_id=emp.id)

    return render_template("receituario_form.html", current_employee=emp,
                           current_user=get_current_user(), rec=None, culturas=culturas, produtos=[], clientes=[], modo="func")

@receituario_bp.route("/func/receituario/<int:rid>")
@_func_login_required
def func_ver(rid):
    from app.models.receituario import Receituario
    emp = _get_emp()
    rec = Receituario.query.filter_by(id=rid, criado_por_func=emp.id).first_or_404()
    return render_template("receituario_view.html", current_employee=emp, current_user=get_current_user(), rec=rec, modo="func")

def extrator_dinamico(item, chaves, padrao=""):
    if not isinstance(item, dict): return padrao
    for k in chaves:
        if k in item and item[k] is not None and item[k] != "":
            return str(item[k])
    return padrao

@receituario_bp.route("/api/receituario/produtos")
def api_produtos():
    q = request.args.get("q", "").strip()
    campo = request.args.get("campo", "nome")
    limit = request.args.get("limit", 20, type=int)

    if not q or len(q) < 2:
        return jsonify([])

    token = _get_agroapi_token()
    if not token:
        return jsonify([{'id': 'erro', 'nome_comercial': '⚠️ ERRO NAS CHAVES', 'ingrediente_ativo': 'Autenticação com MAPA falhou'}])

    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    url = "https://api.cnptia.embrapa.br/agrofit/v1/search/produtos-formulados"
    params = {'marcaComercial': q, 'size': 100} if campo == 'nome' else {'ingredienteAtivo': q, 'size': 100}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=12)
        if response.status_code == 404:
            url = "https://api.cnptia.embrapa.br/agrofit/v1/produtos-formulados"
            response = requests.get(url, headers=headers, params=params, timeout=12)
            
        if response.status_code in (401, 403):
            return jsonify([{'id': 'erro', 'nome_comercial': f'⚠️ ACESSO NEGADO ({response.status_code})', 'ingrediente_ativo': 'API não assinada no AgroAPI'}])
            
        response.raise_for_status()
        dados_embrapa = response.json()
        
        itens = dados_embrapa if isinstance(dados_embrapa, list) else dados_embrapa.get('data', dados_embrapa.get('content', []))
        
        resultado = []
        q_low = q.lower()
        
        for p in itens:
            prod_id = extrator_dinamico(p, ['numero_registro', 'numeroRegistro', 'id', 'codigo_registro', 'registro'])
            if not prod_id: continue
            
            nome = extrator_dinamico(p, ['marca_comercial', 'marcaComercial', 'nome_comercial', 'produto', 'nome', 'marca'])
            if not nome: nome = "Produto Sem Nome"
            
            ia_bruto = p.get('ingrediente_ativo') or p.get('ingredienteAtivo') or p.get('ingredientesAtivos') or p.get('ingredientes_ativos')
            if isinstance(ia_bruto, list):
                ia = ", ".join([extrator_dinamico(x, ['nome', 'ingredienteAtivo', 'ingrediente_ativo']) for x in ia_bruto if isinstance(x, dict)])
            elif isinstance(ia_bruto, dict):
                ia = extrator_dinamico(ia_bruto, ['nome', 'ingredienteAtivo', 'ingrediente_ativo'])
            else:
                ia = str(ia_bruto) if ia_bruto else "Princípio ativo não informado"
                
            if campo == 'nome' and q_low not in nome.lower():
                continue
            if campo == 'ia' and q_low not in ia.lower():
                continue
            
            classe = extrator_dinamico(p, ['classificacao_agronomica', 'classificacaoAgronomica', 'classe'], 'Outros')
            fabricante = extrator_dinamico(p, ['titular_registro', 'titularRegistro', 'fabricante'])
            
            resultado.append({
                'id': prod_id, 
                'nome_comercial': nome,
                'ingrediente_ativo': ia,
                'classe_agronomica': classe,
                'fabricante': fabricante,
                'dose_min': p.get('doseMinima', p.get('dose_minima', 0)),
                'dose_max': p.get('doseMaxima', p.get('dose_maxima', 0)),
                'unidade': p.get('unidadeMedida', p.get('unidade_medida', 'L/ha')),
                'epi_obrigatorio': p.get('epi', 'Verificar bula')
            })
            
            if len(resultado) >= limit:
                break
                
        return jsonify(resultado)

    except Exception as e:
        print(f"Erro de Conexão MAPA: {e}")
        return jsonify([{'id': 'erro', 'nome_comercial': '⚠️ ERRO DE CONEXÃO', 'ingrediente_ativo': 'Servidor da Embrapa demorou.', 'classe_agronomica': 'Outros'}])

@receituario_bp.route("/api/receituario/produto/<pid>/validar")
def api_validar(pid):
    if pid in ('erro', 'vazio', 'null', 'undefined', 'None') or not pid or pid.startswith('REF-'):
        return jsonify({"compatibilidade": "TALVEZ", "motivo": "Revisão agronômica manual da bula necessária."})

    from app.models.receituario import Cultura
    cultura_id = request.args.get("cultura_id", type=int)

    if not cultura_id:
        return jsonify({"compatibilidade": "NAO_INFORMADO", "motivo": "Selecione a cultura."})

    cultura = Cultura.query.get(cultura_id)
    if not cultura:
        return jsonify({"compatibilidade": "NAO", "motivo": "Cultura não encontrada."}), 404

    token = _get_agroapi_token()
    if not token:
         return jsonify({"compatibilidade": "TALVEZ", "motivo": "Falha na conexão com MAPA."})

    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
    url = f"https://api.cnptia.embrapa.br/agrofit/v1/produtos-formulados/{pid}"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        produto_api = response.json()
        
        # AQUI ESTAVA O SEU ERRO ANTIGO: Esta linha garante que listas não quebrem o código!
        if isinstance(produto_api, list):
            produto_api = produto_api[0] if len(produto_api) > 0 else {}
            
        indicacoes = produto_api.get('indicacoesDeUso', produto_api.get('indicacoes_de_uso', []))
        cultura_permitida = False
        restricao_aerea = False
        dose_recomendada = ""
        
        for indicacao in indicacoes:
            cultura_bula = extrator_dinamico(indicacao, ['cultura', 'Cultura']).upper()
            if cultura.nome.upper() in cultura_bula:
                cultura_permitida = True
                dose_recomendada = extrator_dinamico(indicacao, ['dose', 'Dose'])
                modalidade = extrator_dinamico(indicacao, ['modalidadeDeAplicacao', 'modalidade_de_aplicacao']).upper()
                
                if 'TERRESTRE' in modalidade and 'AÉREA' not in modalidade and 'AEREA' not in modalidade:
                    restricao_aerea = True
                break
                
        if not cultura_permitida:
            return jsonify({"compatibilidade": "NAO", "motivo": f"O produto não possui indicação aprovada no MAPA para: {cultura.nome}."})
        if restricao_aerea:
            return jsonify({"compatibilidade": "NAO", "motivo": f"A bula restringe a aplicação exclusivamente terrestre para {cultura.nome}."})

        return jsonify({"compatibilidade": "SIM", "motivo": "", "dose_recomendada": dose_recomendada})

    except Exception as e:
        print(f"Erro Validação MAPA {pid}: {e}")
        return jsonify({"compatibilidade": "TALVEZ", "motivo": "Não foi possível conectar à bula online."})

@receituario_bp.route("/api/receituario/culturas")
def api_culturas():
    from app.models.receituario import Cultura
    cs = Cultura.query.filter_by(ativo=True).order_by(Cultura.nome).all()
    return jsonify([c.to_dict() for c in cs])

def _salvar_receituario(form, rec, func_id=None):
    from app.models.receituario import (Receituario, ItemReceituario)

    auto_migrate_db()

    cultura_id = form.get("cultura_id", type=int)
    if not cultura_id:
        flash("Selecione uma cultura.", "error")
        return redirect(request.url)

    nome_produtor = (form.get("nome_produtor") or "").strip()
    if not nome_produtor:
        flash("Informe o nome do produtor.", "error")
        return redirect(request.url)

    is_new = rec is None
    if is_new:
        rec = Receituario(numero=Receituario.gerar_numero())
        db.session.add(rec)

    rec.nome_produtor         = nome_produtor
    rec.cpf_cnpj_produtor     = form.get("cpf_cnpj_produtor", "")
    rec.telefone_produtor     = form.get("telefone_produtor", "")
    rec.nome_propriedade      = form.get("nome_propriedade", "")
    rec.municipio             = form.get("municipio", "")
    rec.estado                = form.get("estado", "")
    rec.area_ha               = form.get("area_ha", type=float) or 0.0
    rec.talhao                = form.get("talhao", "")
    rec.car                   = form.get("car", "")
    rec.responsavel_tecnico   = form.get("responsavel_tecnico", "")
    rec.crea_cfta             = form.get("crea_cfta", "")
    rec.cpf_rt                = form.get("cpf_rt", "")
    rec.email_rt              = form.get("email_rt", "")
    rec.telefone_rt           = form.get("telefone_rt", "")
    rec.cultura_id            = cultura_id
    rec.diagnostico           = form.get("diagnostico", "")
    rec.praga_alvo            = form.get("praga_alvo", "")
    rec.estagio_fenologico    = form.get("estagio_fenologico", "")
    rec.nivel_acao            = form.get("nivel_acao", "")
    rec.tipo_equipamento      = form.get("tipo_equipamento", "Aeronave agrícola")
    rec.volume_calda          = form.get("volume_calda", type=float)
    rec.num_aplicacoes        = form.get("num_aplicacoes", type=int) or 1
    rec.intervalo_aplicacoes  = form.get("intervalo_aplicacoes", type=int)
    rec.epoca_aplicacao       = form.get("epoca_aplicacao", "")
    rec.observacoes_aplicacao = form.get("observacoes_aplicacao", "")
    rec.observacoes           = form.get("observacoes", "")

    if func_id:
        rec.criado_por_func = func_id

    produto_ids     = form.getlist("produto_id[]")
    produtos_nome   = form.getlist("produto_nome[]")
    produtos_ia     = form.getlist("produto_ia[]")
    produtos_classe = form.getlist("produto_classe[]")
    doses           = form.getlist("dose[]")
    unidades        = form.getlist("unidade[]")
    num_apls        = form.getlist("num_aplicacoes_p[]")

    for item in list(rec.itens):
        db.session.delete(item)

    for i, pid_str in enumerate(produto_ids):
        pid = pid_str.strip()
        if not pid or pid in ('erro', 'vazio', 'null', 'None'):
            continue

        dose_val = None
        try:
            dose_val = float(doses[i]) if i < len(doses) else None
        except (ValueError, TypeError):
            pass

        item = ItemReceituario(
            receituario_id   = rec.id if rec.id else None,
            produto_id_api   = pid,
            produto_nome     = produtos_nome[i] if i < len(produtos_nome) else "Sem Nome",
            produto_ia       = produtos_ia[i] if i < len(produtos_ia) else "Não informado",
            produto_classe   = produtos_classe[i] if i < len(produtos_classe) else "Outros",
            dose             = dose_val,
            unidade          = unidades[i] if i < len(unidades) else "",
            num_aplicacoes   = int(num_apls[i]) if i < len(num_apls) else 1,
            status_validacao = "SIM", 
            motivo_restricao = "",
        )
        rec.itens.append(item)

    db.session.flush()
    db.session.commit()

    acao = form.get("acao", "salvar")
    if acao == "emitir":
        rec.status       = "emitido"
        rec.data_emissao = datetime.utcnow()
        rec.data_validade = date.today() + timedelta(days=90)
        db.session.commit()
        flash(f"Receituário {rec.numero} emitido!", "success")
    else:
        flash(f"Receituário {rec.numero} salvo como rascunho.", "success")

    if func_id:
        return redirect(url_for("receituario.func_ver", rid=rec.id))
    return redirect(url_for("receituario.admin_ver", rid=rec.id))
