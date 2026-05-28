"""Módulo de Receituário Agronômico — Combate Rasante Aviação Agrícola."""
from datetime import datetime, date, timedelta
import requests
import time
import base64
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, jsonify, session, current_app, Response)
from app import db
from app.utils.security import login_required, admin_required, get_current_user, get_current_employee

receituario_bp = Blueprint("receituario", __name__)

# =============================================================================
# CREDENCIAIS DA AGROAPI (EMBRAPA)
# Cole a sua Consumer Key e Consumer Secret abaixo:
# =============================================================================
AGROAPI_KEY = "CEpPWXr0CqatrJPFZJSfBoAxFTka"
AGROAPI_SECRET = "KVYMu619dgmFUSqErSv18OFIIkka"

# Cache para armazenar o token e sua validade na memória do servidor
TOKEN_CACHE = {"access_token": None, "expires_at": 0}

def _get_agroapi_token():
    """Gera um token de acesso seguindo a documentação oficial da Embrapa (Base64)."""
    # Se o token da memória ainda for válido (com 60s de folga), usamos ele
    if TOKEN_CACHE["access_token"] and time.time() < TOKEN_CACHE["expires_at"]:
        return TOKEN_CACHE["access_token"]

    url = "https://api.cnptia.embrapa.br/token"
    
    # Fazendo exatamente a conversão Base64 exigida pela documentação (cURL)
    credenciais = f"{AGROAPI_KEY}:{AGROAPI_SECRET}"
    credenciais_b64 = base64.b64encode(credenciais.encode('utf-8')).decode('utf-8')
    
    headers = {
        "Authorization": f"Basic {credenciais_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "client_credentials"
    }
    
    try:
        response = requests.post(url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        r_json = response.json()
        
        # Salva o novo token e a data de expiração (3600 segundos)
        TOKEN_CACHE["access_token"] = r_json["access_token"]
        TOKEN_CACHE["expires_at"] = time.time() + r_json.get("expires_in", 3600) - 60
        
        return TOKEN_CACHE["access_token"]
    except Exception as e:
        print(f"ERRO DE AUTENTICAÇÃO AGROAPI: {e}")
        return None

# =============================================================================
# Helpers de auth
# =============================================================================
def _is_admin():
    emp = get_current_employee()
    return emp and emp.is_admin

def _employee_pode_receituario():
    emp = get_current_employee()
    return emp and getattr(emp, "pode_receituario", False)

def _get_emp():
    return get_current_employee()

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — lista de receituários
# ─────────────────────────────────────────────────────────────────────────────

@receituario_bp.route("/admin/receituario")
@login_required
@admin_required
def admin_lista():
    from app.models.receituario import Receituario, Cultura
    from app.models.user import User

    q     = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    cult   = request.args.get("cultura", "")

    query = Receituario.query.order_by(Receituario.data_criacao.desc())
    if q:
        query = query.filter(Receituario.nome_produtor.ilike(f"%{q}%") |
                             Receituario.numero.ilike(f"%{q}%"))
    if status:
        query = query.filter_by(status=status)
    if cult:
        query = query.filter_by(cultura_id=int(cult))

    receituarios = query.limit(200).all()
    culturas     = Cultura.query.filter_by(ativo=True).order_by(Cultura.nome).all()

    total     = Receituario.query.count()
    emitidos  = Receituario.query.filter_by(status="emitido").count()
    rascunhos = Receituario.query.filter_by(status="rascunho").count()

    return render_template("receituario_admin.html",
                           current_user=get_current_user(),
                           receituarios=receituarios,
                           culturas=culturas,
                           total=total, emitidos=emitidos, rascunhos=rascunhos,
                           q=q, status_filtro=status, cult_filtro=cult)


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN — criar / editar receituário
# ─────────────────────────────────────────────────────────────────────────────

@receituario_bp.route("/admin/receituario/novo", methods=["GET", "POST"])
@login_required
@admin_required
def admin_novo():
    from app.models.receituario import Cultura
    from app.models.user import User

    culturas  = Cultura.query.filter_by(ativo=True).order_by(Cultura.nome).all()
    clientes  = User.query.filter_by(is_admin=False).order_by(User.name).all()

    if request.method == "POST":
        return _salvar_receituario(request.form, None)

    return render_template("receituario_form.html",
                           current_user=get_current_user(),
                           rec=None, culturas=culturas,
                           produtos=[], clientes=clientes,
                           modo="admin")


@receituario_bp.route("/admin/receituario/<int:rid>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def admin_editar(rid):
    from app.models.receituario import Receituario, Cultura
    from app.models.user import User

    rec       = Receituario.query.get_or_404(rid)
    culturas  = Cultura.query.filter_by(ativo=True).order_by(Cultura.nome).all()
    clientes  = User.query.filter_by(is_admin=False).order_by(User.name).all()

    if request.method == "POST":
        return _salvar_receituario(request.form, rec)

    return render_template("receituario_form.html",
                           current_user=get_current_user(),
                           rec=rec, culturas=culturas,
                           produtos=[], clientes=clientes,
                           modo="admin")


@receituario_bp.route("/admin/receituario/<int:rid>")
@login_required
@admin_required
def admin_ver(rid):
    from app.models.receituario import Receituario
    rec = Receituario.query.get_or_404(rid)
    return render_template("receituario_view.html",
                           current_user=get_current_user(),
                           rec=rec, modo="admin")


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
    rec.status       = "emitido"
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


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONÁRIO — receituário (se tiver permissão)
# ─────────────────────────────────────────────────────────────────────────────

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
    recs = (Receituario.query
            .filter_by(criado_por_func=emp.id)
            .order_by(Receituario.data_criacao.desc())
            .limit(100).all())
    return render_template("receituario_func_lista.html",
                           current_employee=emp, receituarios=recs)


@receituario_bp.route("/func/receituario/novo", methods=["GET", "POST"])
@_func_login_required
def func_novo():
    from app.models.receituario import Cultura
    emp      = _get_emp()
    culturas = Cultura.query.filter_by(ativo=True).order_by(Cultura.nome).all()

    if request.method == "POST":
        return _salvar_receituario(request.form, None, func_id=emp.id)

    return render_template("receituario_form.html",
                           current_employee=emp,
                           current_user=get_current_user(),
                           rec=None, culturas=culturas,
                           produtos=[], clientes=[],
                           modo="func")


@receituario_bp.route("/func/receituario/<int:rid>")
@_func_login_required
def func_ver(rid):
    from app.models.receituario import Receituario
    emp = _get_emp()
    rec = Receituario.query.filter_by(id=rid, criado_por_func=emp.id).first_or_404()
    return render_template("receituario_view.html",
                           current_employee=emp,
                           current_user=get_current_user(),
                           rec=rec, modo="func")


# ─────────────────────────────────────────────────────────────────────────────
# API EMBRAPA — busca de produtos + validação
# ─────────────────────────────────────────────────────────────────────────────

@receituario_bp.route("/api/receituario/produtos")
def api_produtos():
    """Busca produtos. Se houver erro ou falta de assinatura, retorna aviso visual correto."""
    q     = request.args.get("q", "").strip()
    campo = request.args.get("campo", "nome")
    limit = request.args.get("limit", 20, type=int)

    if not q or len(q) < 2:
        return jsonify([])

    token = _get_agroapi_token()
    if not token:
        return jsonify([{
            'id': 'erro',
            'nome_comercial': '⚠️ ERRO NAS CHAVES',
            'ingrediente_ativo': 'Falha ao gerar Token',
            'classe_agronomica': 'Outros',
            'fabricante': 'As chaves do código estão incorretas.'
        }])

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    url = "https://api.cnptia.embrapa.br/agrofit/v1/produtos-formulados"
    params = {'ingredienteAtivo': q} if campo == 'ia' else {'marcaComercial': q}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code in (401, 403):
            return jsonify([{
                'id': 'erro',
                'nome_comercial': f'⚠️ ACESSO NEGADO ({response.status_code})',
                'ingrediente_ativo': 'Você ainda não assinou a API Agrofit no painel da Embrapa!',
                'classe_agronomica': 'Outros',
                'fabricante': 'Acesse o portal > APIs > Agrofit > Aba Assinaturas > Inscrever-se.'
            }])
            
        response.raise_for_status()
        dados_embrapa = response.json()
        
        resultado = []
        itens = dados_embrapa if isinstance(dados_embrapa, list) else dados_embrapa.get('data', dados_embrapa.get('content', []))
        
        for p in itens[:limit]: 
            # Correção crítica do mapeamento: ajustando as chaves que a Embrapa envia para o JS ler
            resultado.append({
                'id': p.get('numeroRegistro', p.get('id')), 
                'nome_comercial': p.get('marcaComercial', p.get('nome_comercial', 'Sem Nome')),
                'ingrediente_ativo': p.get('ingredienteAtivo', p.get('ingrediente_ativo', 'Não informado')),
                'classe_agronomica': p.get('classificacaoAgronomica', p.get('classe_agronomica', 'Não informada')),
                'fabricante': p.get('titularRegistro', p.get('fabricante', '')),
                'dose_min': p.get('doseMinima', 0),
                'dose_max': p.get('doseMaxima', 0),
                'unidade': p.get('unidadeMedida', 'L/ha'),
                'epi_obrigatorio': p.get('epi', 'Verificar bula')
            })
            
        return jsonify(resultado)

    except Exception as e:
        print(f"Erro de Conexão MAPA: {e}")
        return jsonify([{
            'id': 'erro',
            'nome_comercial': '⚠️ ERRO DE CONEXÃO',
            'ingrediente_ativo': 'O servidor do MAPA demorou a responder',
            'classe_agronomica': 'Outros',
            'fabricante': 'Tente novamente em instantes.'
        }])


@receituario_bp.route("/api/receituario/produto/<pid>/validar")
def api_validar(pid):
    """Valida compatibilidade produto × cultura consultando a AgroAPI."""
    from app.models.receituario import Cultura
    cultura_id = request.args.get("cultura_id", type=int)

    if not cultura_id:
        return jsonify({"compatibilidade": "NAO_INFORMADO",
                        "motivo": "Selecione uma cultura antes de adicionar produtos."})

    cultura = Cultura.query.get(cultura_id)
    if not cultura:
        return jsonify({"compatibilidade": "NAO", "motivo": "Cultura não encontrada."}), 404

    # 2. Pede o token dinâmico da função que criamos
    token = _get_agroapi_token()
    if not token:
         return jsonify({"compatibilidade": "TALVEZ", "motivo": "Falha de autenticação com o MAPA. Revise a bula manualmente."})

    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    
    # Busca a bula do produto pelo ID/Registro
    url = f"https://api.cnptia.embrapa.br/agrofit/v1/produtos-formulados/{pid}"

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        produto_api = response.json()
        
        # O Agrofit retorna uma lista de indicacoes (culturas permitidas)
        indicacoes = produto_api.get('indicacoesDeUso', [])
        
        cultura_permitida = False
        restricao_aerea = False
        dose_recomendada = ""
        
        # Verifica se o nome da cultura selecionada está na bula do produto
        for indicacao in indicacoes:
            cultura_bula = indicacao.get('cultura', '').upper()
            
            # Compara o nome da cultura do seu banco com o da API
            if cultura.nome.upper() in cultura_bula:
                cultura_permitida = True
                dose_recomendada = indicacao.get('dose', '')
                
                # Checa restrição de aplicação aérea (modalidade)
                modalidade = indicacao.get('modalidadeDeAplicacao', '').upper()
                # Se não citar 'AÉREA' e citar 'TERRESTRE'
                if 'TERRESTRE' in modalidade and 'AÉREA' not in modalidade:
                    restricao_aerea = True
                break
                
        if not cultura_permitida:
            return jsonify({
                "compatibilidade": "NAO",
                "motivo": f"O produto não possui indicação aprovada no MAPA para a cultura: {cultura.nome}."
            })
            
        if restricao_aerea:
            return jsonify({
                "compatibilidade": "NAO",
                "motivo": f"Proibido para Drone/Avião. A bula restringe a aplicação exclusivamente terrestre para {cultura.nome}."
            })

        # Se passou por tudo, está liberado!
        return jsonify({
            "compatibilidade": "SIM",
            "motivo": "",
            "dose_recomendada": dose_recomendada,
        })

    except requests.exceptions.RequestException as e:
        print(f"Erro ao consultar AgroAPI (Validação): {e}")
        return jsonify({"compatibilidade": "TALVEZ", "motivo": "Não foi possível conectar ao sistema Agrofit para validação automática."})


@receituario_bp.route("/api/receituario/produto/<pid>")
def api_produto_detalhe(pid):
    """Busca detalhes estáticos do produto via API caso seja solicitado na edição."""
    token = _get_agroapi_token()
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/json'
    }
    url = f"https://api.cnptia.embrapa.br/agrofit/v1/produtos-formulados/{pid}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        p = response.json()
        return jsonify({
            'id': p.get('numeroRegistro', p.get('id')),
            'nome_comercial': p.get('marcaComercial', ''),
            'ingrediente_ativo': p.get('ingredienteAtivo', ''),
            'classe_agronomica': p.get('classificacaoAgronomica', ''),
            'fabricante': p.get('titularRegistro', ''),
        })
    except requests.exceptions.RequestException:
        return jsonify({"erro": "Produto não encontrado."}), 404


@receituario_bp.route("/api/receituario/culturas")
def api_culturas():
    from app.models.receituario import Cultura
    cs = Cultura.query.filter_by(ativo=True).order_by(Cultura.nome).all()
    return jsonify([c.to_dict() for c in cs])


# ─────────────────────────────────────────────────────────────────────────────
# Helper — salvar receituário (create / update)
# ─────────────────────────────────────────────────────────────────────────────

def _salvar_receituario(form, rec, func_id=None):
    from app.models.receituario import (Receituario, ItemReceituario)

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

    # Dados do produtor / propriedade
    rec.nome_produtor         = nome_produtor
    rec.cpf_cnpj_produtor     = form.get("cpf_cnpj_produtor", "")
    rec.telefone_produtor     = form.get("telefone_produtor", "")
    rec.nome_propriedade      = form.get("nome_propriedade", "")
    rec.municipio             = form.get("municipio", "")
    rec.estado                = form.get("estado", "")
    rec.area_ha               = form.get("area_ha", type=float) or 0.0
    rec.talhao                = form.get("talhao", "")
    rec.car                   = form.get("car", "")

    # Responsável técnico
    rec.responsavel_tecnico   = form.get("responsavel_tecnico", "")
    rec.crea_cfta             = form.get("crea_cfta", "")
    rec.cpf_rt                = form.get("cpf_rt", "")
    rec.email_rt              = form.get("email_rt", "")
    rec.telefone_rt           = form.get("telefone_rt", "")

    # Dados agronômicos
    rec.cultura_id            = cultura_id
    rec.diagnostico           = form.get("diagnostico", "")
    rec.praga_alvo            = form.get("praga_alvo", "")
    rec.estagio_fenologico    = form.get("estagio_fenologico", "")
    rec.nivel_acao            = form.get("nivel_acao", "")

    # Aplicação
    rec.tipo_equipamento      = form.get("tipo_equipamento", "Aeronave agrícola")
    rec.volume_calda          = form.get("volume_calda", type=float)
    rec.num_aplicacoes        = form.get("num_aplicacoes", type=int) or 1
    rec.intervalo_aplicacoes  = form.get("intervalo_aplicacoes", type=int)
    rec.epoca_aplicacao       = form.get("epoca_aplicacao", "")
    rec.observacoes_aplicacao = form.get("observacoes_aplicacao", "")
    rec.observacoes           = form.get("observacoes", "")

    if func_id:
        rec.criado_por_func = func_id

    # Produtos (array de IDs, nomes e doses vindos do formulário/API)
    produto_ids     = form.getlist("produto_id[]")
    produtos_nome   = form.getlist("produto_nome[]")
    produtos_ia     = form.getlist("produto_ia[]")
    produtos_classe = form.getlist("produto_classe[]")
    doses           = form.getlist("dose[]")
    unidades        = form.getlist("unidade[]")
    num_apls        = form.getlist("num_aplicacoes_p[]")

    # Remover itens antigos
    for item in list(rec.itens):
        db.session.delete(item)

    # Re-adicionar itens
    for i, pid_str in enumerate(produto_ids):
        pid = pid_str.strip()
        if not pid:
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