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


class ProdutoAgricola(db.Model):
    __tablename__       = "produtos_agricolas"
    id                  = db.Column(db.Integer, primary_key=True)
    nome_comercial      = db.Column(db.String(300), nullable=False)
    ingrediente_ativo   = db.Column(db.String(500), nullable=False)
    classe_agronomica   = db.Column(db.String(100))  # Herbicida, Fungicida, Inseticida…
    grupo_quimico       = db.Column(db.String(200))
    fabricante          = db.Column(db.String(300))
    registro_mapa       = db.Column(db.String(100))
    formulacao          = db.Column(db.String(100))  # SC, EC, WP, WG…
    dose_min            = db.Column(db.Float)
    dose_max            = db.Column(db.Float)
    unidade             = db.Column(db.String(50))
    vol_calda_min       = db.Column(db.Float)
    vol_calda_max       = db.Column(db.Float)
    intervalo_seguranca = db.Column(db.Integer)   # dias
    periodo_carencia    = db.Column(db.Integer)   # dias
    classe_toxicologica = db.Column(db.String(50))
    classe_ambiental    = db.Column(db.String(50))
    epi_obrigatorio     = db.Column(db.Text)
    restricoes          = db.Column(db.Text)
    modo_acao           = db.Column(db.String(300))
    ativo               = db.Column(db.Boolean, default=True)

    compatibilidades = db.relationship(
        "ProdutoCultura", backref="produto", lazy=True, cascade="all, delete-orphan"
    )

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
            "periodo_carencia":  self.periodo_carencia,
        }


class ProdutoCultura(db.Model):
    """Tabela de compatibilidade: produto × cultura."""
    __tablename__     = "produto_cultura"
    id                = db.Column(db.Integer, primary_key=True)
    produto_id        = db.Column(db.Integer, db.ForeignKey("produtos_agricolas.id"), nullable=False)
    cultura_id        = db.Column(db.Integer, db.ForeignKey("culturas.id"), nullable=False)
    compatibilidade   = db.Column(db.String(10), default="NAO")   # SIM | NAO | TALVEZ
    motivo            = db.Column(db.Text)
    dose_recomendada  = db.Column(db.String(100))
    dose_maxima       = db.Column(db.String(100))
    observacoes       = db.Column(db.Text)

    cultura = db.relationship("Cultura", backref="compatibilidades")

    def to_dict(self):
        return {
            "produto_id":       self.produto_id,
            "cultura_id":       self.cultura_id,
            "cultura_nome":     self.cultura.nome if self.cultura else "",
            "compatibilidade":  self.compatibilidade,
            "motivo":           self.motivo or "",
            "dose_recomendada": self.dose_recomendada or "",
            "dose_maxima":      self.dose_maxima or "",
            "observacoes":      self.observacoes or "",
        }


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
    produto_id        = db.Column(db.Integer, db.ForeignKey("produtos_agricolas.id"), nullable=False)
    dose              = db.Column(db.Float)
    unidade           = db.Column(db.String(50))
    volume_calda      = db.Column(db.Float)
    num_aplicacoes    = db.Column(db.Integer, default=1)
    status_validacao  = db.Column(db.String(10))   # OK | NAO | TALVEZ
    motivo_restricao  = db.Column(db.Text)
    observacoes       = db.Column(db.Text)

    produto = db.relationship("ProdutoAgricola")


# ─────────────────────────────────────────────────────────────────────────────
# Seed — culturas + produtos + compatibilidades
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

# Estrutura: (nome_comercial, ingrediente_ativo, classe_agron, grupo_quimico,
#             fabricante, registro_mapa, formulacao, dose_min, dose_max, unidade,
#             vol_min, vol_max, int_seg, carencia, classe_tox, classe_amb,
#             epi, restricoes, modo_acao,
#             compat_dict)
# compat_dict = {cultura_nome: ("SIM"|"NAO"|"TALVEZ", motivo, dose_rec, dose_max_str, obs)}

PRODUTOS_SEED = [
    # ── HERBICIDAS ────────────────────────────────────────────────────────────
    (
        "Roundup Transorb R",
        "Glifosato 480 g/L",
        "Herbicida",
        "Glicinas",
        "Monsanto/Bayer",
        "BR02698019",
        "SL",
        1.5, 4.0, "L/ha",
        20, 50,
        30, 0,
        "III", "III",
        "Luva nitrílica, máscara semifacial PFF2, avental impermeável, bota PVC",
        "Não aplicar em ventos > 10 km/h. Proibido perto de cursos d'água.",
        "Inibição da EPSPS — via shiquimato",
        {
            "Soja":           ("SIM",    "",                                      "2,0-3,0 L/ha", "4,0 L/ha", "Dessecação pré-plantio"),
            "Milho":          ("SIM",    "",                                      "2,0-3,0 L/ha", "4,0 L/ha", "Dessecação pré-plantio"),
            "Cana-de-açúcar": ("SIM",    "",                                      "1,5-3,0 L/ha", "4,0 L/ha", "Manejo de plantas daninhas"),
            "Pastagem":       ("SIM",    "",                                      "2,0-3,0 L/ha", "4,0 L/ha", "Reforma de pastagem"),
            "Algodão":        ("SIM",    "",                                      "2,0-3,0 L/ha", "4,0 L/ha", "Somente dessecação pré-plantio"),
            "Trigo":          ("SIM",    "",                                      "2,0-3,0 L/ha", "4,0 L/ha", "Dessecação pré-colheita"),
            "Café":           ("NAO",    "Produto não seletivo — risco de deriva e fitotoxidez grave ao cafeeiro", "", "", ""),
            "Feijão":         ("TALVEZ", "Apenas dessecação pré-plantio. Respeitar intervalo de 10 dias antes do plantio", "2,0 L/ha", "3,0 L/ha", ""),
            "Citros":         ("NAO",    "Não registrado para citros. Risco de fitotoxidez severa",                    "", "", ""),
            "Arroz":          ("TALVEZ", "Somente manejo em área total antes da inundação",                            "2,0 L/ha", "3,0 L/ha", ""),
            "Sorgo":          ("SIM",    "",                                      "2,0-3,0 L/ha", "4,0 L/ha", "Dessecação pré-plantio"),
            "Girassol":       ("SIM",    "",                                      "2,0-3,0 L/ha", "4,0 L/ha", "Dessecação pré-plantio"),
        },
    ),
    (
        "2,4-D Amina 720",
        "2,4-D (sal dimetilamina) 720 g/L",
        "Herbicida",
        "Ácidos ariloxialcanóicos",
        "Dow AgroSciences",
        "BR0510219",
        "SL",
        0.5, 1.5, "L/ha",
        20, 40,
        14, 0,
        "II", "III",
        "Luva nitrílica, máscara PFF2, óculos vedados, avental impermeável",
        "Não aplicar com ventos > 10 km/h. Alta volatilidade — risco de deriva em dicotiledôneas sensíveis.",
        "Mimetismo auxínico — crescimento descontrolado",
        {
            "Soja":           ("NAO",    "Soja é extremamente sensível ao 2,4-D. Causa epinastia e severa queda de produtividade", "", "", ""),
            "Milho":          ("SIM",    "",                                        "0,5-1,0 L/ha", "1,5 L/ha", "Aplicar nos estádios V4-V6. Não usar em florescimento"),
            "Cana-de-açúcar": ("TALVEZ", "Uso restrito a condições específicas. Consultar receituário atualizado",     "0,5-0,8 L/ha", "1,0 L/ha", ""),
            "Pastagem":       ("SIM",    "",                                        "0,8-1,5 L/ha", "1,5 L/ha", "Controle de eudicotiledôneas — não prejudica gramíneas"),
            "Algodão":        ("NAO",    "Algodão é altamente sensível ao 2,4-D. Causa deformação severa de folhas e frutos", "", "", ""),
            "Trigo":          ("SIM",    "",                                        "0,5-1,0 L/ha", "1,5 L/ha", "Aplicar no afilhamento (até 3 perfilhos). Evitar florescimento"),
            "Café":           ("NAO",    "Cafeeiro é dicotiledônea sensível — risco de fitotoxidez grave",             "", "", ""),
            "Feijão":         ("NAO",    "Feijão é leguminosa sensível ao 2,4-D",                                      "", "", ""),
            "Citros":         ("NAO",    "Alta sensibilidade à deriva — pode causar danos irreversíveis",               "", "", ""),
            "Arroz":          ("TALVEZ", "Apenas em arroz de sequeiro em estádio específico",                          "0,5-0,8 L/ha", "1,0 L/ha", ""),
            "Sorgo":          ("SIM",    "",                                        "0,5-1,0 L/ha", "1,5 L/ha", "Verificar estádio antes da aplicação"),
            "Girassol":       ("NAO",    "Girassol é dicotiledônea sensível",                                          "", "", ""),
        },
    ),
    (
        "Gramoxone 200",
        "Paraquat 200 g/L",
        "Herbicida",
        "Bipiridílio",
        "Syngenta",
        "BR004017",
        "SL",
        1.5, 3.0, "L/ha",
        20, 50,
        7, 0,
        "I", "III",
        "EPI completo — luva neoprene, máscara PFF3, óculos vedados, avental, bota. PRODUTO ALTAMENTE TÓXICO",
        "Produto proibido para uso amador. Uso restrito a aplicadores certificados. Altamente tóxico para humanos.",
        "Inibição do fotossistema I — geração de radicais livres",
        {
            "Soja":     ("SIM",    "", "1,5-2,5 L/ha", "3,0 L/ha", "Dessecação pré-colheita ou pré-plantio"),
            "Milho":    ("SIM",    "", "1,5-2,5 L/ha", "3,0 L/ha", "Dessecação"),
            "Algodão":  ("SIM",    "", "1,5-2,5 L/ha", "3,0 L/ha", "Dessecação"),
            "Trigo":    ("SIM",    "", "1,5-2,5 L/ha", "3,0 L/ha", "Dessecação pré-colheita"),
            "Pastagem": ("SIM",    "", "2,0-3,0 L/ha", "3,0 L/ha", "Reforma de pastagem"),
            "Café":     ("TALVEZ", "Uso em manejo de área — evitar contato com folhagem e troncos", "1,5 L/ha", "2,0 L/ha", ""),
            "Feijão":   ("SIM",    "", "1,5-2,0 L/ha", "3,0 L/ha", "Dessecação pré-colheita"),
            "Citros":   ("TALVEZ", "Uso localizado em entrelinhas — evitar contato direto com plantas", "1,5 L/ha", "2,0 L/ha", ""),
            "Cana-de-açúcar": ("SIM", "", "2,0-3,0 L/ha", "3,0 L/ha", ""),
            "Arroz":    ("SIM",    "", "1,5-2,0 L/ha", "3,0 L/ha", "Dessecação pré-colheita em arroz de sequeiro"),
            "Sorgo":    ("SIM",    "", "1,5-2,5 L/ha", "3,0 L/ha", "Dessecação"),
            "Girassol": ("SIM",    "", "1,5-2,0 L/ha", "3,0 L/ha", "Dessecação pré-colheita"),
        },
    ),
    (
        "Atrazina 500 SC",
        "Atrazina 500 g/L",
        "Herbicida",
        "Triazinas",
        "Syngenta",
        "BR00003",
        "SC",
        3.0, 6.0, "L/ha",
        20, 40,
        30, 60,
        "III", "II",
        "Luva nitrílica, máscara PFF2, avental impermeável",
        "Contaminante de águas subterrâneas. Proibido em áreas < 200m de cursos d'água.",
        "Inibição do fotossistema II — bloqueio da fotossíntese",
        {
            "Milho":          ("SIM",    "", "3,0-5,0 L/ha", "6,0 L/ha", "Pré ou pós-emergência precoce"),
            "Cana-de-açúcar": ("SIM",    "", "3,0-6,0 L/ha", "6,0 L/ha", "Pré-emergência"),
            "Sorgo":          ("SIM",    "", "2,0-3,0 L/ha", "4,0 L/ha", "Apenas pré-emergência"),
            "Soja":           ("NAO",    "Soja não possui tolerância à atrazina — fitotoxidez severa",                   "", "", ""),
            "Algodão":        ("NAO",    "Algodão é sensível à atrazina",                                                "", "", ""),
            "Trigo":          ("NAO",    "Trigo não tolera atrazina",                                                    "", "", ""),
            "Pastagem":       ("TALVEZ", "Uso restrito a pastagens estabelecidas em formulações específicas",            "2,0-3,0 L/ha", "4,0 L/ha", ""),
            "Café":           ("NAO",    "Não registrado para café",                                                      "", "", ""),
            "Feijão":         ("NAO",    "Feijão não tolera atrazina",                                                   "", "", ""),
            "Citros":         ("NAO",    "Não registrado para citros",                                                   "", "", ""),
            "Arroz":          ("NAO",    "Arroz não tolera atrazina",                                                    "", "", ""),
            "Girassol":       ("NAO",    "Girassol é sensível à atrazina",                                               "", "", ""),
        },
    ),
    (
        "Velpar K WG",
        "Hexazinona 125 g/kg + Diuron 625 g/kg",
        "Herbicida",
        "Triazinona + Ureia substituída",
        "Du Pont",
        "BR07802009",
        "WG",
        2.0, 4.0, "kg/ha",
        15, 30,
        30, 60,
        "III", "II",
        "Luva nitrílica, máscara PFF2, avental, bota PVC",
        "Exclusivo para cana-de-açúcar. Altamente persistente no solo. Proibido perto de cursos d'água.",
        "Inibição do fotossistema II",
        {
            "Cana-de-açúcar": ("SIM",    "", "2,0-4,0 kg/ha", "4,0 kg/ha", "Pré-emergência em cana planta e soca"),
            "Soja":           ("NAO",    "Produto exclusivo para cana — sem registro para soja",                  "", "", ""),
            "Milho":          ("NAO",    "Produto exclusivo para cana — sem registro para milho",                 "", "", ""),
            "Algodão":        ("NAO",    "Produto exclusivo para cana",                                           "", "", ""),
            "Trigo":          ("NAO",    "Produto exclusivo para cana",                                           "", "", ""),
            "Pastagem":       ("NAO",    "Produto exclusivo para cana",                                           "", "", ""),
            "Café":           ("NAO",    "Produto exclusivo para cana",                                           "", "", ""),
            "Feijão":         ("NAO",    "Produto exclusivo para cana",                                           "", "", ""),
            "Citros":         ("NAO",    "Produto exclusivo para cana",                                           "", "", ""),
            "Arroz":          ("NAO",    "Produto exclusivo para cana",                                           "", "", ""),
            "Sorgo":          ("NAO",    "Produto exclusivo para cana",                                           "", "", ""),
            "Girassol":       ("NAO",    "Produto exclusivo para cana",                                           "", "", ""),
        },
    ),
    (
        "Select 240 EC",
        "Cletodim 240 g/L",
        "Herbicida",
        "Ciclohexanodionas",
        "Arysta / UPL",
        "BR02302019",
        "EC",
        0.3, 0.6, "L/ha",
        20, 40,
        21, 0,
        "III", "III",
        "Luva nitrílica, máscara PFF2, avental, óculos",
        "Seletivo para dicotiledôneas. Não aplicar em gramíneas cultivadas.",
        "Inibição da ACC-ase — bloqueia biossíntese de lipídios em gramíneas",
        {
            "Soja":           ("SIM",    "", "0,3-0,5 L/ha", "0,6 L/ha", "Controle de gramíneas em pós-emergência"),
            "Algodão":        ("SIM",    "", "0,3-0,5 L/ha", "0,6 L/ha", "Controle de gramíneas"),
            "Feijão":         ("SIM",    "", "0,3-0,5 L/ha", "0,6 L/ha", "Controle de gramíneas"),
            "Café":           ("SIM",    "", "0,4-0,6 L/ha", "0,6 L/ha", "Controle de capim em café"),
            "Citros":         ("SIM",    "", "0,4-0,6 L/ha", "0,6 L/ha", "Controle de gramíneas em citros"),
            "Milho":          ("NAO",    "Milho é gramínea — cletodim causa fitotoxidez severa",                  "", "", ""),
            "Trigo":          ("NAO",    "Trigo é gramínea — produto causa morte da cultura",                    "", "", ""),
            "Cana-de-açúcar": ("NAO",    "Cana é gramínea — produto não seletivo",                               "", "", ""),
            "Pastagem":       ("NAO",    "Pastagem é composta por gramíneas — produto destrutivo",                "", "", ""),
            "Arroz":          ("NAO",    "Arroz é gramínea",                                                     "", "", ""),
            "Sorgo":          ("NAO",    "Sorgo é gramínea",                                                     "", "", ""),
            "Girassol":       ("SIM",    "", "0,4-0,6 L/ha", "0,6 L/ha", "Controle de gramíneas em girassol"),
        },
    ),

    # ── FUNGICIDAS ────────────────────────────────────────────────────────────
    (
        "Priori Xtra",
        "Azoxistrobina 200 g/L + Ciproconazol 80 g/L",
        "Fungicida",
        "Estrobilurina + Triazol",
        "Syngenta",
        "BR06302019",
        "SC",
        0.2, 0.3, "L/ha",
        30, 50,
        14, 21,
        "III", "III",
        "Luva nitrílica, máscara PFF2, avental, óculos",
        "Máximo 2 aplicações sequenciais. Alternar com fungicidas de diferente modo de ação.",
        "Inibição do complexo III mitocondrial (Qo) + Inibição da biossíntese de ergosterol (DMI)",
        {
            "Soja":     ("SIM", "", "0,25-0,3 L/ha",  "0,3 L/ha", "Controle de ferrugem-asiática, antracnose e oídio"),
            "Milho":    ("SIM", "", "0,2-0,3 L/ha",   "0,3 L/ha", "Controle de helmintosporiose e ferrugem"),
            "Algodão":  ("SIM", "", "0,2-0,3 L/ha",   "0,3 L/ha", "Controle de ramulária e mancha-angular"),
            "Trigo":    ("SIM", "", "0,2-0,25 L/ha",  "0,3 L/ha", "Controle de septoriose, ferrugem e brusone"),
            "Feijão":   ("SIM", "", "0,2-0,3 L/ha",   "0,3 L/ha", "Controle de mancha-angular"),
            "Café":     ("TALVEZ", "Registro em processo. Verificar bula atualizada", "0,2 L/ha", "0,3 L/ha", ""),
            "Cana-de-açúcar": ("TALVEZ", "Uso experimental — verificar registro atual", "0,2-0,3 L/ha", "0,3 L/ha", ""),
            "Arroz":    ("SIM", "", "0,2-0,25 L/ha",  "0,3 L/ha", "Controle de brusone"),
            "Sorgo":    ("SIM", "", "0,2-0,25 L/ha",  "0,3 L/ha", "Controle de antracnose e ferrugem"),
            "Pastagem": ("NAO", "Não registrado para pastagem", "", "", ""),
            "Citros":   ("NAO", "Não registrado para citros", "", "", ""),
            "Girassol": ("SIM", "", "0,2-0,3 L/ha",   "0,3 L/ha", "Controle de Sclerotinia"),
        },
    ),
    (
        "Nativo SC",
        "Tebuconazol 100 g/L + Trifloxistrobina 50 g/L",
        "Fungicida",
        "Triazol + Estrobilurina",
        "Bayer CropScience",
        "BR06102019",
        "SC",
        0.5, 1.0, "L/ha",
        20, 40,
        14, 21,
        "III", "III",
        "Luva nitrílica, máscara PFF2, avental impermeável",
        "Não aplicar em temperaturas > 30°C. Máximo 3 aplicações/safra.",
        "Inibição da C14-desmetilase (DMI) + Inibição do complexo III (Qo)",
        {
            "Soja":           ("SIM", "", "0,5-0,75 L/ha",  "1,0 L/ha", "Ferrugem, antracnose, mancha-alvo"),
            "Milho":          ("SIM", "", "0,5-0,75 L/ha",  "1,0 L/ha", "Helmintosporiose, ferrugem, antracnose"),
            "Algodão":        ("SIM", "", "0,5-0,75 L/ha",  "1,0 L/ha", "Ramulária, cercospora"),
            "Trigo":          ("SIM", "", "0,5-0,75 L/ha",  "1,0 L/ha", "Septoriose, giberela, ferrugem"),
            "Cana-de-açúcar": ("SIM", "", "0,75-1,0 L/ha",  "1,0 L/ha", "Ferrugem-laranja, carvão"),
            "Café":           ("SIM", "", "0,5-0,75 L/ha",  "1,0 L/ha", "Ferrugem do café — aplicação preventiva"),
            "Feijão":         ("SIM", "", "0,5-0,75 L/ha",  "1,0 L/ha", "Antracnose, ferrugem"),
            "Arroz":          ("SIM", "", "0,5-0,75 L/ha",  "1,0 L/ha", "Brusone"),
            "Sorgo":          ("SIM", "", "0,5-0,75 L/ha",  "1,0 L/ha", "Antracnose, ferrugem"),
            "Girassol":       ("SIM", "", "0,5-0,75 L/ha",  "1,0 L/ha", "Sclerotinia, alternaria"),
            "Pastagem":       ("TALVEZ", "Registro limitado — verificar bula", "0,5 L/ha", "0,75 L/ha", ""),
            "Citros":         ("TALVEZ", "Uso em processo de registro — consultar MAPA", "0,5 L/ha", "0,75 L/ha", ""),
        },
    ),
    (
        "Fox Xpro",
        "Bixafen 60 g/L + Tebuconazol 120 g/L + Trifloxistrobina 60 g/L",
        "Fungicida",
        "SDHI + Triazol + Estrobilurina",
        "Bayer CropScience",
        "BR08302019",
        "SC",
        0.4, 0.6, "L/ha",
        15, 30,
        14, 21,
        "III", "III",
        "Luva nitrílica, máscara PFF2, avental, óculos de segurança",
        "Produto de alto valor — máximo 2 aplicações/safra. Não misturar com herbicidas de contato.",
        "Inibição do complexo II (SDHI) + DMI + Qo — tripla ação",
        {
            "Soja":     ("SIM", "", "0,4-0,5 L/ha", "0,6 L/ha", "Controle superior de ferrugem e doenças foliares"),
            "Milho":    ("SIM", "", "0,4-0,5 L/ha", "0,6 L/ha", "Helmintosporiose, ferrugem, antracnose"),
            "Trigo":    ("SIM", "", "0,4-0,5 L/ha", "0,6 L/ha", "Giberela, septoriose, ferrugem"),
            "Algodão":  ("SIM", "", "0,4-0,5 L/ha", "0,6 L/ha", "Ramulária — muito eficiente"),
            "Feijão":   ("SIM", "", "0,4-0,5 L/ha", "0,6 L/ha", ""),
            "Sorgo":    ("SIM", "", "0,4-0,5 L/ha", "0,6 L/ha", ""),
            "Girassol": ("SIM", "", "0,4-0,5 L/ha", "0,6 L/ha", ""),
            "Cana-de-açúcar": ("TALVEZ", "Uso experimental — registro pendente completo", "0,4 L/ha", "0,5 L/ha", ""),
            "Café":     ("TALVEZ", "Verificar registro atualizado no MAPA", "0,4 L/ha", "0,5 L/ha", ""),
            "Arroz":    ("TALVEZ", "Uso em desenvolvimento — consultar bula vigente", "0,4 L/ha", "0,5 L/ha", ""),
            "Pastagem": ("NAO",    "Não registrado para pastagem", "", "", ""),
            "Citros":   ("NAO",    "Não registrado para citros", "", "", ""),
        },
    ),
    (
        "Folicur 200 CE",
        "Tebuconazol 200 g/L",
        "Fungicida",
        "Triazol",
        "Bayer CropScience",
        "BR00302019",
        "EC",
        0.5, 1.0, "L/ha",
        20, 40,
        14, 30,
        "III", "III",
        "Luva nitrílica, máscara PFF2, avental, óculos",
        "Máximo 3 aplicações/safra. Intervalo mínimo de 14 dias.",
        "Inibição da biossíntese de ergosterol — classe DMI",
        {
            "Soja":           ("SIM", "", "0,5-0,75 L/ha", "1,0 L/ha", "Ferrugem, antracnose"),
            "Milho":          ("SIM", "", "0,5-0,75 L/ha", "1,0 L/ha", "Helmintosporiose, ferrugem"),
            "Trigo":          ("SIM", "", "0,5-0,75 L/ha", "1,0 L/ha", "Oídio, septoriose, giberela"),
            "Cana-de-açúcar": ("SIM", "", "0,75-1,0 L/ha", "1,0 L/ha", "Ferrugem-laranja"),
            "Café":           ("SIM", "", "0,5-0,75 L/ha", "1,0 L/ha", "Ferrugem do café"),
            "Algodão":        ("SIM", "", "0,5-0,75 L/ha", "1,0 L/ha", "Ramulária"),
            "Feijão":         ("SIM", "", "0,5-0,75 L/ha", "1,0 L/ha", "Antracnose"),
            "Arroz":          ("SIM", "", "0,5-0,75 L/ha", "1,0 L/ha", "Brusone"),
            "Sorgo":          ("SIM", "", "0,5-0,75 L/ha", "1,0 L/ha", ""),
            "Girassol":       ("SIM", "", "0,5-0,75 L/ha", "1,0 L/ha", ""),
            "Pastagem":       ("TALVEZ", "Uso limitado — verificar registro", "0,5 L/ha", "0,75 L/ha", ""),
            "Citros":         ("TALVEZ", "Verificar registro MAPA para citros", "0,5 L/ha", "0,75 L/ha", ""),
        },
    ),
    (
        "Dithane NT",
        "Mancozebe 750 g/kg",
        "Fungicida",
        "Ditiocarbamato",
        "Dow AgroSciences",
        "BR002019",
        "WP",
        1.5, 3.0, "kg/ha",
        20, 40,
        3, 10,
        "IV", "IV",
        "Luva nitrílica, máscara PFF1, avental",
        "Produto protetor — aplicar preventivamente. Pode causar resistência se usado isolado por muitas safras.",
        "Inibição de enzimas sulfidrilas — multissítio protetor",
        {
            "Soja":     ("SIM", "", "1,5-2,0 kg/ha", "3,0 kg/ha", "Preventivo para mancha-parda, mela"),
            "Milho":    ("SIM", "", "1,5-2,0 kg/ha", "3,0 kg/ha", "Preventivo para helmintosporiose"),
            "Algodão":  ("SIM", "", "1,5-2,0 kg/ha", "3,0 kg/ha", "Preventivo para doenças foliares"),
            "Café":     ("SIM", "", "2,0-3,0 kg/ha", "3,0 kg/ha", "Ferrugem e cercospora em café"),
            "Citros":   ("SIM", "", "2,0-3,0 kg/ha", "3,0 kg/ha", "Melanose, verrugose"),
            "Feijão":   ("SIM", "", "1,5-2,0 kg/ha", "3,0 kg/ha", "Mancha-angular, antracnose"),
            "Trigo":    ("SIM", "", "1,5-2,0 kg/ha", "3,0 kg/ha", "Preventivo multidoenças"),
            "Arroz":    ("SIM", "", "1,5-2,0 kg/ha", "3,0 kg/ha", "Preventivo para brusone"),
            "Girassol": ("SIM", "", "1,5-2,0 kg/ha", "3,0 kg/ha", ""),
            "Sorgo":    ("SIM", "", "1,5-2,0 kg/ha", "3,0 kg/ha", ""),
            "Cana-de-açúcar": ("TALVEZ", "Uso limitado — verificar registro específico", "1,5 kg/ha", "2,0 kg/ha", ""),
            "Pastagem": ("NAO", "Não registrado para pastagem", "", "", ""),
        },
    ),

    # ── INSETICIDAS ───────────────────────────────────────────────────────────
    (
        "Karate Zeon 50 CS",
        "Lambda-cialotrina 50 g/L",
        "Inseticida",
        "Piretroide",
        "Syngenta",
        "BR00202019",
        "CS",
        0.1, 0.3, "L/ha",
        20, 50,
        7, 14,
        "III", "III",
        "Luva nitrílica, máscara PFF2, avental, bota, óculos",
        "Tóxico para abelhas — não aplicar em florescimento. Respeitar horários de menor atividade de polinizadores.",
        "Agonista dos canais de sódio — paralisia nervosa por contato e ingestão",
        {
            "Soja":           ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Lagartas, percevejos, pulgões"),
            "Milho":          ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Lagarta-do-cartucho, cigarrinha"),
            "Algodão":        ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Bicudo, pulgão, tripes"),
            "Cana-de-açúcar": ("SIM", "", "0,15-0,25 L/ha","0,3 L/ha", "Broca-da-cana, cigarrinha"),
            "Trigo":          ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Pulgões, lagartas"),
            "Café":           ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Broca-do-café, lagartas"),
            "Algodão":        ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Bicudo, lagartas"),
            "Feijão":         ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Lagartas, pulgões"),
            "Citros":         ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Lagarta-minadora, pulgões"),
            "Arroz":          ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Bicheira, lagarta-boiadeira"),
            "Pastagem":       ("SIM", "", "0,15-0,25 L/ha","0,3 L/ha", "Cigarrinha-das-pastagens"),
            "Sorgo":          ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Pulgão, lagarta-do-cartucho"),
            "Girassol":       ("SIM", "", "0,1-0,2 L/ha", "0,3 L/ha", "Lagartas, tripes"),
        },
    ),
    (
        "Engeo Pleno SC",
        "Tiametoxam 141 g/L + Lambda-cialotrina 106 g/L",
        "Inseticida",
        "Neonicotinoide + Piretroide",
        "Syngenta",
        "BR08502019",
        "SC",
        0.2, 0.3, "L/ha",
        20, 50,
        14, 21,
        "II", "III",
        "Luva neoprene, máscara PFF2, avental impermeável, bota PVC, óculos",
        "Altamente tóxico para abelhas e organismos aquáticos. Não aplicar em florescimento nem próximo a corpos hídricos.",
        "Inibição nicotínica dos receptores de acetilcolina + agonismo de canais de sódio",
        {
            "Soja":           ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", "Percevejo-verde, lagarta-da-soja, mosca-branca"),
            "Milho":          ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", "Lagarta-do-cartucho, cigarrinha"),
            "Algodão":        ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", "Bicudo, mosca-branca, tripes"),
            "Cana-de-açúcar": ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", "Broca, cigarrinha"),
            "Trigo":          ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", "Pulgões, lagartas"),
            "Café":           ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", "Broca-do-café, ácaros-rajados"),
            "Feijão":         ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", "Lagartas, pulgões"),
            "Arroz":          ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", "Bicheira, percevejo-do-colmo"),
            "Pastagem":       ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", "Cigarrinha-das-pastagens"),
            "Citros":         ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", "Minadora, psilídeo"),
            "Sorgo":          ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", ""),
            "Girassol":       ("SIM", "", "0,2-0,25 L/ha", "0,3 L/ha", ""),
        },
    ),
    (
        "Lorsban 480 BR",
        "Clorpirifós 480 g/L",
        "Inseticida",
        "Organofosforado",
        "Dow AgroSciences",
        "BR000319",
        "EC",
        0.5, 2.0, "L/ha",
        20, 50,
        7, 21,
        "II", "II",
        "Luva neoprene, máscara PFF3 com filtro para vapores orgânicos, avental impermeável, bota PVC, óculos vedados",
        "PRODUTO DE USO RESTRITO. Tóxico para aves, abelhas e organismos aquáticos. Proibido em perímetros urbanos.",
        "Inibição da acetilcolinesterase — acúmulo de acetilcolina nas sinapses",
        {
            "Soja":           ("SIM", "", "0,5-1,0 L/ha",  "2,0 L/ha", "Lagartas, percevejos — uso cuiativo"),
            "Milho":          ("SIM", "", "0,5-1,0 L/ha",  "2,0 L/ha", "Lagarta-do-cartucho (curativo)"),
            "Algodão":        ("SIM", "", "0,5-1,0 L/ha",  "2,0 L/ha", "Bicudo, tripes"),
            "Cana-de-açúcar": ("SIM", "", "1,0-2,0 L/ha",  "2,0 L/ha", "Broca-da-cana"),
            "Citros":         ("SIM", "", "0,5-1,5 L/ha",  "2,0 L/ha", "Minadora, pulgões"),
            "Café":           ("SIM", "", "0,5-1,0 L/ha",  "2,0 L/ha", "Broca-do-café, lagartas"),
            "Trigo":          ("SIM", "", "0,5-1,0 L/ha",  "2,0 L/ha", "Pulgões, lagartas"),
            "Feijão":         ("SIM", "", "0,5-1,0 L/ha",  "2,0 L/ha", "Lagartas, vaquinhas"),
            "Arroz":          ("SIM", "", "0,5-1,0 L/ha",  "2,0 L/ha", "Lagarta-boiadeira"),
            "Pastagem":       ("TALVEZ", "Uso com restrições — consultar bula e legislação estadual", "0,5 L/ha", "1,0 L/ha", ""),
            "Sorgo":          ("SIM", "", "0,5-1,0 L/ha",  "2,0 L/ha", ""),
            "Girassol":       ("SIM", "", "0,5-1,0 L/ha",  "2,0 L/ha", ""),
        },
    ),
    (
        "Belt SC",
        "Flubendiamida 480 g/L",
        "Inseticida",
        "Diamida antranílica",
        "Bayer CropScience",
        "BR09302019",
        "SC",
        0.05, 0.15, "L/ha",
        20, 50,
        14, 21,
        "III", "III",
        "Luva nitrílica, máscara PFF2, avental",
        "Alta seletividade — baixo risco a inimigos naturais. Máximo 2 aplicações/safra.",
        "Ativação dos receptores de rianodina — liberação incontrolada de cálcio intracelular",
        {
            "Soja":     ("SIM", "", "0,05-0,1 L/ha",  "0,15 L/ha", "Lagartas — alta eficiência"),
            "Milho":    ("SIM", "", "0,05-0,1 L/ha",  "0,15 L/ha", "Lagarta-do-cartucho, spodoptera"),
            "Algodão":  ("SIM", "", "0,05-0,1 L/ha",  "0,15 L/ha", "Alabama, lagartas em geral"),
            "Feijão":   ("SIM", "", "0,05-0,1 L/ha",  "0,15 L/ha", "Lagartas"),
            "Trigo":    ("SIM", "", "0,05-0,1 L/ha",  "0,15 L/ha", "Lagartas"),
            "Café":     ("SIM", "", "0,05-0,1 L/ha",  "0,15 L/ha", "Broca-do-café"),
            "Sorgo":    ("SIM", "", "0,05-0,1 L/ha",  "0,15 L/ha", ""),
            "Girassol": ("SIM", "", "0,05-0,1 L/ha",  "0,15 L/ha", ""),
            "Cana-de-açúcar": ("SIM", "", "0,08-0,15 L/ha", "0,15 L/ha", "Broca-da-cana"),
            "Arroz":    ("SIM", "", "0,05-0,1 L/ha",  "0,15 L/ha", ""),
            "Pastagem": ("TALVEZ", "Verificar registro para pragas em pastagem", "0,05 L/ha", "0,1 L/ha", ""),
            "Citros":   ("TALVEZ", "Registro em algumas culturas cítricas — verificar bula", "0,05 L/ha", "0,1 L/ha", ""),
        },
    ),
    (
        "Tracer SC",
        "Espinosade 480 g/L",
        "Inseticida",
        "Espinosina",
        "Dow AgroSciences",
        "BR001219",
        "SC",
        0.05, 0.12, "L/ha",
        20, 40,
        7, 14,
        "IV", "III",
        "Luva nitrílica, máscara PFF1, avental, óculos",
        "Produto de origem biológica — menor impacto ambiental. Máximo 2 aplicações consecutivas.",
        "Agonista nicotínico + agonista alostérico dos receptores de GABA",
        {
            "Soja":     ("SIM", "", "0,05-0,08 L/ha", "0,12 L/ha", "Lagartas — excelente para MIP"),
            "Algodão":  ("SIM", "", "0,05-0,08 L/ha", "0,12 L/ha", "Tripes, lagartas"),
            "Milho":    ("SIM", "", "0,05-0,08 L/ha", "0,12 L/ha", "Lagarta-do-cartucho"),
            "Café":     ("SIM", "", "0,05-0,08 L/ha", "0,12 L/ha", "Broca-do-café"),
            "Feijão":   ("SIM", "", "0,05-0,08 L/ha", "0,12 L/ha", "Lagartas"),
            "Trigo":    ("SIM", "", "0,05-0,08 L/ha", "0,12 L/ha", ""),
            "Girassol": ("SIM", "", "0,05-0,08 L/ha", "0,12 L/ha", ""),
            "Sorgo":    ("SIM", "", "0,05-0,08 L/ha", "0,12 L/ha", ""),
            "Arroz":    ("SIM", "", "0,05-0,08 L/ha", "0,12 L/ha", ""),
            "Cana-de-açúcar": ("TALVEZ", "Verificar registro atualizado para cana", "0,05 L/ha", "0,1 L/ha", ""),
            "Pastagem": ("TALVEZ", "Verificar registro", "0,05 L/ha", "0,08 L/ha", ""),
            "Citros":   ("SIM", "", "0,05-0,1 L/ha", "0,12 L/ha", "Minadora, tripes"),
        },
    ),

    # ── REGULADORES DE CRESCIMENTO ────────────────────────────────────────────
    (
        "Ethrel 480",
        "Etefon 480 g/L",
        "Regulador de Crescimento",
        "Ácido fosfônico",
        "Bayer CropScience",
        "BR00602019",
        "SL",
        0.3, 0.5, "L/ha",
        15, 25,
        30, 30,
        "III", "III",
        "Luva nitrílica, máscara PFF2, avental, óculos, bota",
        "Maturador exclusivo para cana-de-açúcar. Aplicar 60-90 dias antes da colheita. Temperatura ideal: 22-28°C.",
        "Liberação de etileno endógeno — maturação dos colmos",
        {
            "Cana-de-açúcar": ("SIM",    "", "0,3-0,5 L/ha", "0,5 L/ha", "Maturação antecipada — aumento do teor de sacarose"),
            "Soja":           ("NAO",    "Etefon causa aceleração da senescência em soja — desfoliação prematura e queda de produtividade", "", "", ""),
            "Milho":          ("TALVEZ", "Uso experimental em milho-pipoca para antecipação da colheita — não recomendado em milho-grão", "0,2 L/ha", "0,3 L/ha", ""),
            "Algodão":        ("TALVEZ", "Usado como desfoliante + maturador — apenas em condições específicas de colheita mecanizada", "0,3 L/ha", "0,5 L/ha", ""),
            "Trigo":          ("TALVEZ", "Pode ser usado para reduzir acamamento — verificar dose e cultivar", "0,3 L/ha", "0,4 L/ha", ""),
            "Café":           ("TALVEZ", "Usado para uniformizar maturação — aplicação muito específica", "0,3 L/ha", "0,5 L/ha", ""),
            "Arroz":          ("TALVEZ", "Uso experimental — consultar especialista", "0,2 L/ha", "0,3 L/ha", ""),
            "Pastagem":       ("NAO",    "Sem registro e sem benefício agronômico em pastagem", "", "", ""),
            "Citros":         ("TALVEZ", "Usado para desverdecimento de frutos — uso muito específico", "0,2 L/ha", "0,4 L/ha", ""),
            "Feijão":         ("NAO",    "Sem registro e sem benefício para feijão", "", "", ""),
            "Sorgo":          ("NAO",    "Sem registro para sorgo",                 "", "", ""),
            "Girassol":       ("NAO",    "Sem registro para girassol",              "", "", ""),
        },
    ),
    (
        "Moddus 250 EC",
        "Trinexapaque-etílico 250 g/L",
        "Regulador de Crescimento",
        "Ciclohexanodiona",
        "Syngenta",
        "BR01002019",
        "EC",
        0.4, 0.8, "L/ha",
        20, 35,
        14, 7,
        "IV", "III",
        "Luva nitrílica, máscara PFF1, avental",
        "Redutor de crescimento — previne acamamento. Não aplicar em período de seca severa.",
        "Inibição da biossíntese de giberelinas — redução do entrenó",
        {
            "Trigo":          ("SIM",    "", "0,4-0,6 L/ha", "0,8 L/ha", "Prevenção de acamamento — estádio do afilhamento"),
            "Cana-de-açúcar": ("SIM",    "", "0,6-0,8 L/ha", "0,8 L/ha", "Controle do florescimento indesejado"),
            "Arroz":          ("SIM",    "", "0,4-0,6 L/ha", "0,8 L/ha", "Prevenção de acamamento"),
            "Sorgo":          ("TALVEZ", "Uso experimental para controle de altura",  "0,4 L/ha", "0,6 L/ha", ""),
            "Soja":           ("NAO",    "Sem registro e pode prejudicar florescimento e enchimento de grãos", "", "", ""),
            "Milho":          ("NAO",    "Pode reduzir produtividade em milho",        "", "", ""),
            "Algodão":        ("NAO",    "Sem registro para algodão",                  "", "", ""),
            "Pastagem":       ("NAO",    "Sem registro e sem benefício em pastagem",    "", "", ""),
            "Café":           ("NAO",    "Sem registro para café",                      "", "", ""),
            "Feijão":         ("NAO",    "Sem registro para feijão",                    "", "", ""),
            "Citros":         ("NAO",    "Sem registro para citros",                    "", "", ""),
            "Girassol":       ("NAO",    "Sem registro para girassol",                  "", "", ""),
        },
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Função de seed
# ─────────────────────────────────────────────────────────────────────────────

def seed_receituario():
    """Popula culturas, produtos e compatibilidades se as tabelas estiverem vazias."""
    if Cultura.query.count() > 0:
        return  # já populado

    # Culturas
    cultura_map = {}
    for nome, nome_cient in CULTURAS_SEED:
        c = Cultura(nome=nome, nome_cientifico=nome_cient, ativo=True)
        db.session.add(c)
        db.session.flush()
        cultura_map[nome] = c.id

    # Produtos + compatibilidades
    for dados in PRODUTOS_SEED:
        (nome_com, ia, classe, grupo, fab, reg, form,
         d_min, d_max, un, v_min, v_max, int_seg, carencia,
         cl_tox, cl_amb, epi, rest, modo, compat) = dados

        p = ProdutoAgricola(
            nome_comercial=nome_com, ingrediente_ativo=ia,
            classe_agronomica=classe, grupo_quimico=grupo,
            fabricante=fab, registro_mapa=reg, formulacao=form,
            dose_min=d_min, dose_max=d_max, unidade=un,
            vol_calda_min=v_min, vol_calda_max=v_max,
            intervalo_seguranca=int_seg, periodo_carencia=carencia,
            classe_toxicologica=cl_tox, classe_ambiental=cl_amb,
            epi_obrigatorio=epi, restricoes=rest, modo_acao=modo,
            ativo=True,
        )
        db.session.add(p)
        db.session.flush()

        for cult_nome, (comp, motivo, dose_rec, dose_max_str, obs) in compat.items():
            cid = cultura_map.get(cult_nome)
            if cid:
                db.session.add(ProdutoCultura(
                    produto_id=p.id, cultura_id=cid,
                    compatibilidade=comp, motivo=motivo,
                    dose_recomendada=dose_rec, dose_maxima=dose_max_str,
                    observacoes=obs,
                ))

    db.session.commit()
