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

# ─────────────────────────────────────────────────────────────────────────────
# ProdutoAgricola + ProdutoCultura — banco local de produtos para aviação
# (fallback quando AGROFIT API não está disponível)
# ─────────────────────────────────────────────────────────────────────────────

class ProdutoAgricola(db.Model):
    __tablename__       = "produtos_agricolas"
    id                  = db.Column(db.Integer, primary_key=True)
    nome_comercial      = db.Column(db.String(300), nullable=False)
    ingrediente_ativo   = db.Column(db.String(500), nullable=False)
    classe_agronomica   = db.Column(db.String(100))
    fabricante          = db.Column(db.String(300))
    registro_mapa       = db.Column(db.String(100))
    formulacao          = db.Column(db.String(100))
    dose_min            = db.Column(db.Float)
    dose_max            = db.Column(db.Float)
    unidade             = db.Column(db.String(50))
    epi_obrigatorio     = db.Column(db.Text)
    aplicacao_aerea     = db.Column(db.String(12), default="VERIFICAR")
    motivo_aerea        = db.Column(db.Text)
    ativo               = db.Column(db.Boolean, default=True)

    compatibilidades = db.relationship("ProdutoCultura", backref="produto", lazy=True,
                                       cascade="all, delete-orphan", foreign_keys="ProdutoCultura.produto_id")

    def to_dict(self):
        return {
            "id": self.id,
            "nome_comercial":    self.nome_comercial,
            "ingrediente_ativo": self.ingrediente_ativo,
            "classe_agronomica": self.classe_agronomica,
            "fabricante":        self.fabricante,
            "registro_mapa":     self.registro_mapa,
            "dose_min":          self.dose_min,
            "dose_max":          self.dose_max,
            "unidade":           self.unidade,
            "epi_obrigatorio":   self.epi_obrigatorio,
            "aplicacao_aerea":   self.aplicacao_aerea or "VERIFICAR",
            "motivo_aerea":      self.motivo_aerea or "",
        }


class ProdutoCultura(db.Model):
    __tablename__    = "produto_cultura"
    id               = db.Column(db.Integer, primary_key=True)
    produto_id       = db.Column(db.Integer, db.ForeignKey("produtos_agricolas.id"), nullable=False)
    cultura_id       = db.Column(db.Integer, db.ForeignKey("culturas.id"), nullable=False)
    compatibilidade  = db.Column(db.String(10), default="NAO")
    motivo           = db.Column(db.Text)
    dose_recomendada = db.Column(db.String(100))
    observacoes      = db.Column(db.Text)

    cultura = db.relationship("Cultura", backref="compat_produtos")

    def to_dict(self):
        return {
            "produto_id":      self.produto_id,
            "cultura_id":      self.cultura_id,
            "cultura_nome":    self.cultura.nome if self.cultura else "",
            "compatibilidade": self.compatibilidade,
            "motivo":          self.motivo or "",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Seed de produtos locais
# ─────────────────────────────────────────────────────────────────────────────

_P = [
    # (nome, ia, classe, fab, mapa, form, d_min, d_max, un, epi, aerea, mot_aerea,
    #  {cultura: (SIM|NAO|TALVEZ, motivo)})
    ("Roundup Transorb R","Glifosato 480 g/L","Herbicida","Bayer","BR02698019","SL",
     1.5,4.0,"L/ha","Luva nitrílica, máscara PFF2, avental, bota","NAO",
     "Glifosato PROIBIDO para aplicação aérea — alto risco de deriva.",
     {"Soja":("SIM","Dessecação pré-plantio"),"Milho":("SIM","Dessecação pré-plantio"),
      "Cana-de-açúcar":("NAO","Não autorizado via aérea"),"Algodão":("SIM","Só dessecação pré-plantio"),
      "Trigo":("SIM","Dessecação pré-colheita"),"Pastagem":("SIM","Reforma de pastagem")}),

    ("2,4-D Amina 720","2,4-D 720 g/L","Herbicida","Dow AgroSciences","BR0510219","SL",
     0.5,1.5,"L/ha","Luva neoprene, máscara PFF2, avental, óculos","NAO",
     "2,4-D PROIBIDO para aplicação aérea — altíssima volatilidade e deriva.",
     {"Milho":("SIM","Terrestre apenas"),"Pastagem":("SIM","Controle de eudicotiledôneas"),
      "Trigo":("SIM","Terrestre apenas"),"Soja":("NAO","Altamente sensível ao 2,4-D"),
      "Algodão":("NAO","Sensível — deriva causa danos graves")}),

    ("Velpar K WG","Hexazinona 125 g/kg + Diuron 625 g/kg","Herbicida","Du Pont","BR07802009","WG",
     2.0,4.0,"kg/ha","Luva nitrílica, máscara PFF2, avental, bota","SIM",
     "Registrado para aplicação aérea em cana-de-açúcar pelo MAPA.",
     {"Cana-de-açúcar":("SIM","Pré-emergência cana planta e soca"),
      **{c:("NAO","Produto exclusivo para cana-de-açúcar.") for c in
         ["Soja","Milho","Algodão","Trigo","Arroz","Pastagem","Café","Feijão","Citros","Sorgo","Girassol"]}}),

    ("Atrazina 500 SC","Atrazina 500 g/L","Herbicida","Syngenta","BR00003","SC",
     3.0,6.0,"L/ha","Luva nitrílica, máscara PFF2, avental","SIM",
     "Registrada para aplicação aérea em milho e cana pelo MAPA.",
     {"Milho":("SIM","Pré ou pós-emergência precoce"),
      "Cana-de-açúcar":("SIM","Pré-emergência"),
      "Sorgo":("SIM","Pré-emergência"),
      "Soja":("NAO","Fitotoxidez severa em soja")}),

    ("Diuron Nortox 500 SC","Diuron 500 g/L","Herbicida","Nortox","BR04502019","SC",
     2.0,4.0,"L/ha","Luva nitrílica, máscara PFF2, avental","SIM",
     "Diuron registrado para aplicação aérea em cana e algodão.",
     {"Cana-de-açúcar":("SIM","Pré-emergência"),"Algodão":("SIM","Pré-emergência"),
      "Soja":("NAO","Sem registro"),"Milho":("NAO","Sem registro")}),

    ("Tebuthiuron 500 SC (Combine)","Tebuthiuron 500 g/L","Herbicida","Dow","BR02202019","SC",
     1.2,2.0,"L/ha","Luva nitrílica, máscara PFF2, avental, bota","SIM",
     "Tebuthiuron com registro para aplicação aérea em cana — MAPA.",
     {"Cana-de-açúcar":("SIM","Controle de plantas daninhas em cana"),
      "Pastagem":("TALVEZ","Verificar registro específico"),
      "Soja":("NAO","Sem registro"),"Milho":("NAO","Sem registro")}),

    ("Gramoxone 200","Paraquat 200 g/L","Herbicida","Syngenta","BR004017","SL",
     1.5,3.0,"L/ha","EPI COMPLETO — luva neoprene, PFF3, óculos vedados, avental, bota","SIM",
     "Paraquat com registro para aplicação aérea em dessecação. Requer operadores certificados.",
     {"Soja":("SIM","Dessecação pré-colheita/pré-plantio"),
      "Milho":("SIM","Dessecação"),"Algodão":("SIM","Dessecação"),
      "Trigo":("SIM","Dessecação pré-colheita"),"Pastagem":("SIM","Reforma"),
      "Cana-de-açúcar":("SIM","Manejo de plantas daninhas"),
      "Feijão":("SIM","Dessecação pré-colheita"),"Arroz":("SIM","Pré-colheita")}),

    ("Select 240 EC","Cletodim 240 g/L","Herbicida","UPL","BR02302019","EC",
     0.3,0.6,"L/ha","Luva nitrílica, máscara PFF2, avental","SIM",
     "Cletodim registrado para aplicação aérea em soja, algodão e café.",
     {"Soja":("SIM","Controle de gramíneas pós-emergência"),
      "Algodão":("SIM","Controle de gramíneas"),"Feijão":("SIM",""),
      "Café":("SIM",""),"Citros":("SIM",""),
      "Milho":("NAO","Produto MATA gramíneas — cultura incompatível"),
      "Trigo":("NAO","Produto MATA gramíneas"),"Cana-de-açúcar":("NAO","Gramínea — incompatível")}),

    ("Priori Xtra SC","Azoxistrobina 200 g/L + Ciproconazol 80 g/L","Fungicida","Syngenta","BR06302019","SC",
     0.2,0.3,"L/ha","Luva nitrílica, máscara PFF2, avental, óculos","SIM",
     "Azoxistrobina + Ciproconazol registrados para aplicação aérea.",
     {"Soja":("SIM","Ferrugem, antracnose, oídio"),"Milho":("SIM","Helmintosporiose, ferrugem"),
      "Algodão":("SIM","Ramulária"),"Trigo":("SIM","Septoriose, ferrugem"),
      "Feijão":("SIM","Mancha-angular"),"Arroz":("SIM","Brusone"),
      "Sorgo":("SIM",""),"Girassol":("SIM",""),
      "Café":("TALVEZ","Verificar registro atualizado"),
      "Cana-de-açúcar":("TALVEZ","Uso em desenvolvimento")}),

    ("Nativo SC","Tebuconazol 100 g/L + Trifloxistrobina 50 g/L","Fungicida","Bayer","BR06102019","SC",
     0.5,1.0,"L/ha","Luva nitrílica, máscara PFF2, avental","SIM",
     "Tebuconazol + Trifloxistrobina registrados para aplicação aérea em diversas culturas.",
     {"Soja":("SIM","Ferrugem, antracnose, mancha-alvo"),
      "Milho":("SIM","Helmintosporiose, ferrugem"),"Algodão":("SIM","Ramulária"),
      "Trigo":("SIM","Septoriose, giberela"),"Cana-de-açúcar":("SIM","Ferrugem-laranja"),
      "Café":("SIM","Ferrugem do café"),"Feijão":("SIM","Antracnose"),
      "Arroz":("SIM","Brusone"),"Sorgo":("SIM",""),"Girassol":("SIM","")}),

    ("Fox Xpro","Bixafen 60 g/L + Tebuconazol 120 g/L + Trifloxistrobina 60 g/L","Fungicida","Bayer","BR08302019","SC",
     0.4,0.6,"L/ha","Luva nitrílica, máscara PFF2, avental, óculos","SIM",
     "Tripla mistura com registro para aplicação aérea em soja, milho e algodão.",
     {"Soja":("SIM","Controle superior de ferrugem"),"Milho":("SIM","Helmintosporiose"),
      "Trigo":("SIM","Giberela, septoriose"),"Algodão":("SIM","Ramulária"),
      "Feijão":("SIM",""),"Sorgo":("SIM",""),"Girassol":("SIM","")}),

    ("Folicur 200 CE","Tebuconazol 200 g/L","Fungicida","Bayer","BR00302019","EC",
     0.5,1.0,"L/ha","Luva nitrílica, máscara PFF2, avental, óculos","SIM",
     "Tebuconazol registrado para aplicação aérea em múltiplas culturas.",
     {"Soja":("SIM",""),"Milho":("SIM",""),"Trigo":("SIM",""),"Cana-de-açúcar":("SIM","Ferrugem-laranja"),
      "Café":("SIM","Ferrugem do café"),"Algodão":("SIM",""),"Feijão":("SIM",""),
      "Arroz":("SIM","Brusone"),"Sorgo":("SIM",""),"Girassol":("SIM","")}),

    ("Opera SC","Piraclostrobina 133 g/L + Epoxiconazol 50 g/L","Fungicida","BASF","BR07002019","SC",
     0.5,0.75,"L/ha","Luva nitrílica, máscara PFF2, avental","SIM",
     "Opera SC registrado para aplicação aérea.",
     {"Soja":("SIM","Ferrugem, DFC"),"Milho":("SIM","Helmintosporiose"),
      "Trigo":("SIM","Septoriose, giberela"),"Café":("SIM","Ferrugem"),
      "Feijão":("SIM",""),"Algodão":("SIM",""),"Arroz":("SIM","Brusone")}),

    ("Dithane NT","Mancozebe 750 g/kg","Fungicida","Dow","BR002019","WP",
     1.5,3.0,"kg/ha","Luva nitrílica, máscara PFF1, avental","SIM",
     "Mancozebe registrado para aplicação aérea em diversas culturas.",
     {"Soja":("SIM","Preventivo"),"Milho":("SIM","Preventivo"),"Algodão":("SIM",""),
      "Café":("SIM","Ferrugem"),"Citros":("SIM","Melanose"),"Feijão":("SIM",""),
      "Trigo":("SIM",""),"Arroz":("SIM",""),"Girassol":("SIM",""),"Sorgo":("SIM","")}),

    ("Karate Zeon 50 CS","Lambda-cialotrina 50 g/L","Inseticida","Syngenta","BR00202019","CS",
     0.1,0.3,"L/ha","Luva nitrílica, máscara PFF2, avental, bota, óculos","SIM",
     "Lambda-cialotrina registrada para aplicação aérea em múltiplas culturas.",
     {"Soja":("SIM",""),"Milho":("SIM",""),"Algodão":("SIM",""),"Cana-de-açúcar":("SIM",""),
      "Trigo":("SIM",""),"Café":("SIM",""),"Feijão":("SIM",""),"Citros":("SIM",""),
      "Arroz":("SIM",""),"Pastagem":("SIM",""),"Sorgo":("SIM",""),"Girassol":("SIM","")}),

    ("Engeo Pleno SC","Tiametoxam 141 g/L + Lambda-cialotrina 106 g/L","Inseticida","Syngenta","BR08502019","SC",
     0.2,0.3,"L/ha","Luva neoprene, máscara PFF2, avental, bota, óculos","SIM",
     "Tiametoxam + Lambda-cialotrina registrados para aplicação aérea.",
     {"Soja":("SIM","Percevejo, lagarta, mosca-branca"),"Milho":("SIM","Lagarta-do-cartucho"),
      "Algodão":("SIM","Bicudo, mosca-branca"),"Cana-de-açúcar":("SIM","Broca, cigarrinha"),
      "Trigo":("SIM",""),"Café":("SIM",""),"Feijão":("SIM",""),"Arroz":("SIM",""),
      "Pastagem":("SIM","Cigarrinha"),"Citros":("SIM",""),"Sorgo":("SIM",""),"Girassol":("SIM","")}),

    ("Lorsban 480 BR","Clorpirifós 480 g/L","Inseticida","Dow","BR000319","EC",
     0.5,2.0,"L/ha","Luva neoprene, máscara PFF3 + filtro orgânico, avental, bota, óculos","SIM",
     "Clorpirifós com registro para aplicação aérea. Requer operadores certificados.",
     {"Soja":("SIM",""),"Milho":("SIM",""),"Algodão":("SIM",""),"Cana-de-açúcar":("SIM",""),
      "Citros":("SIM",""),"Café":("SIM",""),"Trigo":("SIM",""),"Feijão":("SIM",""),
      "Arroz":("SIM",""),"Sorgo":("SIM",""),"Girassol":("SIM","")}),

    ("Decis 25 EC","Deltametrina 25 g/L","Inseticida","Bayer","BR01102019","EC",
     0.3,0.6,"L/ha","Luva nitrílica, máscara PFF2, avental, bota","SIM",
     "Deltametrina registrada para aplicação aérea.",
     {"Soja":("SIM",""),"Milho":("SIM",""),"Algodão":("SIM",""),"Cana-de-açúcar":("SIM",""),
      "Trigo":("SIM",""),"Café":("SIM",""),"Feijão":("SIM",""),"Arroz":("SIM",""),
      "Pastagem":("SIM",""),"Sorgo":("SIM",""),"Girassol":("SIM",""),"Citros":("SIM","")}),

    ("Belt SC","Flubendiamida 480 g/L","Inseticida","Bayer","BR09302019","SC",
     0.05,0.15,"L/ha","Luva nitrílica, máscara PFF2, avental","SIM",
     "Flubendiamida registrada para aplicação aérea em soja, milho e algodão.",
     {"Soja":("SIM","Lagartas"),"Milho":("SIM","Spodoptera"),"Algodão":("SIM",""),
      "Feijão":("SIM",""),"Trigo":("SIM",""),"Café":("SIM","Broca"),
      "Cana-de-açúcar":("SIM","Broca-da-cana"),"Sorgo":("SIM",""),"Girassol":("SIM",""),
      "Arroz":("SIM","")}),

    ("Tracer SC","Espinosade 480 g/L","Inseticida","Dow","BR001219","SC",
     0.05,0.12,"L/ha","Luva nitrílica, máscara PFF1, avental, óculos","SIM",
     "Espinosade — biológico registrado para aplicação aérea. Excelente para MIP.",
     {"Soja":("SIM","Lagartas"),"Algodão":("SIM","Tripes, lagartas"),"Milho":("SIM",""),
      "Café":("SIM","Broca"),"Feijão":("SIM",""),"Trigo":("SIM",""),"Girassol":("SIM",""),
      "Sorgo":("SIM",""),"Arroz":("SIM",""),"Citros":("SIM","Minadora")}),

    ("Ampligo 150 ZC","Clorantraniliprole 100 g/L + Lambda-cialotrina 50 g/L","Inseticida","Syngenta","BR09502019","ZC",
     0.25,0.35,"L/ha","Luva nitrílica, máscara PFF2, avental, óculos","SIM",
     "Diamida + piretroide registrados para aplicação aérea.",
     {"Soja":("SIM",""),"Milho":("SIM",""),"Algodão":("SIM",""),"Cana-de-açúcar":("SIM",""),
      "Trigo":("SIM",""),"Feijão":("SIM",""),"Arroz":("SIM",""),"Sorgo":("SIM",""),
      "Café":("SIM","Broca-do-café"),"Citros":("SIM",""),"Girassol":("SIM","")}),

    ("Bt (Bacillus thuringiensis) WP","Bacillus thuringiensis var. kurstaki","Bioinsumo","Certis","BR09702019","WP",
     0.5,1.5,"kg/ha","Máscara PFF1, luva — baixíssima toxicidade","SIM",
     "Bioinsumo MAPA amplamente utilizado e permitido para aplicação aérea.",
     {"Soja":("SIM","Lagartas — MIP"),"Milho":("SIM",""),"Algodão":("SIM",""),
      "Cana-de-açúcar":("SIM",""),"Trigo":("SIM",""),"Arroz":("SIM",""),
      "Café":("SIM",""),"Feijão":("SIM",""),"Citros":("SIM",""),
      "Sorgo":("SIM",""),"Girassol":("SIM",""),"Pastagem":("SIM","")}),

    ("Beauveria bassiana WP","Beauveria bassiana","Bioinsumo","Koppert","BR09802019","WP",
     0.5,2.0,"kg/ha","Máscara PFF1, luva — produto biológico","SIM",
     "Fungo entomopatogênico registrado para aplicação aérea. Aceito em org. orgânica.",
     {"Soja":("SIM",""),"Milho":("SIM",""),"Algodão":("SIM",""),"Cana-de-açúcar":("SIM",""),
      "Trigo":("SIM",""),"Arroz":("SIM",""),"Café":("SIM",""),"Feijão":("SIM",""),
      "Citros":("SIM",""),"Sorgo":("SIM",""),"Girassol":("SIM",""),"Pastagem":("SIM","")}),

    ("Cotesia flavipes","Cotesia flavipes","Biológico / Parasitoide","IAC","BR10002019","—",
     200000,300000,"parasitoides/ha","Nenhum EPI específico — produto biológico vivo","SIM",
     "Cotesia flavipes: bioinsumo fundamental no controle da broca-da-cana. Liberação aérea autorizada.",
     {"Cana-de-açúcar":("SIM","Controle biológico da broca — Diatraea saccharalis"),
      **{c:("NAO","Parasitoide específico para broca-da-cana.") for c in
         ["Soja","Milho","Algodão","Trigo","Arroz","Pastagem","Café","Feijão","Citros","Sorgo","Girassol"]}}),

    ("Ethrel 480","Etefon 480 g/L","Regulador de Crescimento","Bayer","BR00602019","SL",
     0.3,0.5,"L/ha","Luva nitrílica, máscara PFF2, avental, óculos, bota","SIM",
     "Etefon registrado para aplicação aérea em cana (maturação) e algodão (desfolha).",
     {"Cana-de-açúcar":("SIM","Maturação — aumento do teor de sacarose"),
      "Algodão":("TALVEZ","Desfoliante — uso em condições específicas"),
      "Soja":("NAO","Sem registro — causa senescência prematura"),
      "Milho":("NAO","Sem registro"),"Pastagem":("NAO","Sem registro")}),

    ("Moddus 250 EC","Trinexapaque-etílico 250 g/L","Regulador de Crescimento","Syngenta","BR01002019","EC",
     0.4,0.8,"L/ha","Luva nitrílica, máscara PFF1, avental","SIM",
     "Trinexapaque registrado para aplicação aérea em trigo e cana.",
     {"Trigo":("SIM","Prevenção de acamamento"),
      "Cana-de-açúcar":("SIM","Controle do florescimento"),
      "Arroz":("SIM","Prevenção de acamamento"),
      "Sorgo":("TALVEZ","Uso experimental"),
      "Soja":("NAO","Sem registro"),"Milho":("NAO","Sem registro")}),

    ("Produto Genérico Sem Registro","Não identificado","Desconhecido","—","SEM REGISTRO","—",
     0,0,"—","NENHUM — produto ilegal","NAO",
     "Produto SEM REGISTRO no MAPA. Aplicação é ILEGAL conforme Lei nº 7.802/1989.",
     {c:("NAO","Produto sem registro MAPA — aplicação ILEGAL. Lei nº 7.802/1989.") for c in
      ["Soja","Milho","Cana-de-açúcar","Algodão","Trigo","Arroz","Pastagem","Café","Feijão","Citros","Sorgo","Girassol"]}),
]


def seed_produtos():
    """Popula a tabela de produtos agrícolas se ainda estiver vazia."""
    if ProdutoAgricola.query.count() > 0:
        return

    # Mapeia nome de cultura para id
    cult_map = {c.nome: c.id for c in Cultura.query.all()}
    if not cult_map:
        return  # culturas ainda não foram seed

    for row in _P:
        (nome, ia, classe, fab, mapa, form, dmin, dmax, un,
         epi, aerea, mot_aerea, compat) = row

        p = ProdutoAgricola(
            nome_comercial=nome, ingrediente_ativo=ia,
            classe_agronomica=classe, fabricante=fab,
            registro_mapa=mapa, formulacao=form,
            dose_min=dmin, dose_max=dmax, unidade=un,
            epi_obrigatorio=epi,
            aplicacao_aerea=aerea, motivo_aerea=mot_aerea,
            ativo=True,
        )
        db.session.add(p)
        db.session.flush()

        for cult_nome, (comp, motivo) in compat.items():
            cid = cult_map.get(cult_nome)
            if cid:
                db.session.add(ProdutoCultura(
                    produto_id=p.id, cultura_id=cid,
                    compatibilidade=comp, motivo=motivo,
                ))

    db.session.commit()
