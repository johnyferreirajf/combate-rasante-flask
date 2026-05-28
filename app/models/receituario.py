from datetime import datetime, date
from app import db


# ─────────────────────────────────────────────────────────────────────────────
# Modelos
# ─────────────────────────────────────────────────────────────────────────────

class Cultura(db.Model):
    __tablename__ = "culturas"
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(100), nullable=False, unique=True)
    nome_cientifico = db.Column(db.String(200))
    descricao     = db.Column(db.Text)
    ativo         = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {"id": self.id, "nome": self.nome}


class Receituario(db.Model):
    __tablename__         = "receituarios"
    id                    = db.Column(db.Integer, primary_key=True)
    numero                = db.Column(db.String(50), unique=True, nullable=False)

    # Produtor
    nome_produtor         = db.Column(db.String(300), nullable=False)
    cpf_cnpj_produtor     = db.Column(db.String(30))
    telefone_produtor     = db.Column(db.String(30))

    # Propriedade
    nome_propriedade      = db.Column(db.String(300))
    municipio             = db.Column(db.String(200))
    estado                = db.Column(db.String(2))
    area_ha               = db.Column(db.Float)
    talhao                = db.Column(db.String(200))
    car                   = db.Column(db.String(100))

    # Responsável técnico
    responsavel_tecnico   = db.Column(db.String(300))
    crea_cfta             = db.Column(db.String(100))
    cpf_rt                = db.Column(db.String(30))
    email_rt              = db.Column(db.String(200))
    telefone_rt           = db.Column(db.String(30))

    # Dados agronômicos
    cultura_id            = db.Column(db.Integer, db.ForeignKey("culturas.id"))
    diagnostico           = db.Column(db.Text)
    praga_alvo            = db.Column(db.String(500))
    estagio_fenologico    = db.Column(db.String(300))
    nivel_acao            = db.Column(db.String(200))

    # Aplicação aérea
    tipo_equipamento      = db.Column(db.String(200), default="Aeronave agrícola")
    volume_calda          = db.Column(db.Float)
    num_aplicacoes        = db.Column(db.Integer, default=1)
    intervalo_aplicacoes  = db.Column(db.Integer)
    epoca_aplicacao       = db.Column(db.String(300))
    observacoes_aplicacao = db.Column(db.Text)

    # Controle
    status                = db.Column(db.String(20), default="rascunho")
    criado_por_user       = db.Column(db.Integer)
    criado_por_func       = db.Column(db.Integer)
    data_criacao          = db.Column(db.DateTime, default=datetime.utcnow)
    data_emissao          = db.Column(db.DateTime)
    data_validade         = db.Column(db.Date)
    observacoes           = db.Column(db.Text)

    cultura = db.relationship("Cultura", backref="receituarios")
    itens   = db.relationship(
        "ItemReceituario", backref="receituario", lazy=True, cascade="all, delete-orphan"
    )

    @staticmethod
    def gerar_numero():
        import random
        ano = datetime.now().year
        return f"CR-{ano}-{random.randint(1000, 9999):04d}"

    @property
    def status_geral_validacao(self):
        """OK | NAO | TALVEZ | SEM_ITENS"""
        if not self.itens:
            return "SEM_ITENS"
        if any(i.status_validacao == "NAO" for i in self.itens):
            return "NAO"
        if any(i.status_validacao == "TALVEZ" for i in self.itens):
            return "TALVEZ"
        return "OK"


class ItemReceituario(db.Model):
    __tablename__     = "itens_receituario"
    id                = db.Column(db.Integer, primary_key=True)
    receituario_id    = db.Column(db.Integer, db.ForeignKey("receituarios.id"), nullable=False)
    
    # ID do produto retornado pela AgroAPI (Embrapa)
    produto_id_api    = db.Column(db.String(100), nullable=False)
    
    # Dados salvos estaticamente para não depender da API na hora de visualizar o PDF
    produto_nome      = db.Column(db.String(300))
    produto_ia        = db.Column(db.String(500))
    produto_classe    = db.Column(db.String(100))
    
    dose              = db.Column(db.Float)
    unidade           = db.Column(db.String(50))
    volume_calda      = db.Column(db.Float)
    num_aplicacoes    = db.Column(db.Integer, default=1)
    status_validacao  = db.Column(db.String(10))   # OK | NAO | TALVEZ
    motivo_restricao  = db.Column(db.Text)
    observacoes       = db.Column(db.Text)


# ─────────────────────────────────────────────────────────────────────────────
# Seed — Apenas Culturas
# ─────────────────────────────────────────────────────────────────────────────

CULTURAS_SEED = [
    ("Soja",           "Glycine max"),
    ("Milho",          "Zea mays"),
    ("Cana-de-açúcar", "Saccharum officinarum"),
    ("Algodão",        "Gossypium hirsutum"),
    ("Trigo",          "Triticum aestivum"),
    ("Arroz",          "Oryza sativa"),
    ("Pastagem",       "Brachiaria spp. / Panicum spp."),
    ("Café",           "Coffea arabica"),
    ("Feijão",         "Phaseolus vulgaris"),
    ("Citros",         "Citrus spp."),
    ("Sorgo",          "Sorghum bicolor"),
    ("Girassol",       "Helianthus annuus"),
]

def seed_receituario():
    """Popula apenas a tabela de culturas. Os produtos agora vêm da AgroAPI."""
    if Cultura.query.count() > 0:
        return  # já populado

    for nome, nome_cient in CULTURAS_SEED:
        c = Cultura(nome=nome, nome_cientifico=nome_cient, ativo=True)
        db.session.add(c)
    
    db.session.commit()