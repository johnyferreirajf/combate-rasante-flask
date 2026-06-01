import os
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")
    # Render usa proxy reverso — ProxyFix faz url_for gerar https:// corretamente
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # garante BASE_DIR/instance (onde o config.py da raiz aponta)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.makedirs(os.path.join(project_root, "instance"), exist_ok=True)

    # (opcional) garante também a instance do Flask
    os.makedirs(app.instance_path, exist_ok=True)

    # Banco
    db.init_app(app)
    migrate.init_app(app, db)

    # Importa modelos antes de criar tabelas (necessário para db.create_all enxergar tudo)
    from app import models  # noqa: F401

    # Importa models diretamente
    from app.models.user import User
    from app.models.employee import Employee

    # Cria as tabelas e cria admin padrão (se não existir)
    with app.app_context():
        db.create_all()

        # ── Migration segura: adicionar colunas/tabelas novas sem apagar dados ──
        try:
            from sqlalchemy import text as _text
            with db.engine.connect() as _conn:
                _migrations = [
                    # ── Receituário Agronômico ──────────────────────────────
                    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS pode_receituario BOOLEAN NOT NULL DEFAULT FALSE",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS cpf_cnpj VARCHAR(30)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS telefone VARCHAR(30)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS nome_propriedade VARCHAR(300)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS municipio VARCHAR(200)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS estado VARCHAR(2)",
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS car VARCHAR(100)",
                    "ALTER TABLE produtos_agricolas ADD COLUMN IF NOT EXISTS aplicacao_aerea VARCHAR(12) DEFAULT 'VERIFICAR'",
                    "ALTER TABLE produtos_agricolas ADD COLUMN IF NOT EXISTS motivo_aerea TEXT",
                    """CREATE TABLE IF NOT EXISTS culturas (
                        id SERIAL PRIMARY KEY,
                        nome VARCHAR(100) NOT NULL UNIQUE,
                        nome_cientifico VARCHAR(200),
                        descricao TEXT,
                        ativo BOOLEAN DEFAULT TRUE
                    )""",
                    """CREATE TABLE IF NOT EXISTS produtos_agricolas (
                        id SERIAL PRIMARY KEY,
                        nome_comercial VARCHAR(300) NOT NULL,
                        ingrediente_ativo VARCHAR(500) NOT NULL,
                        classe_agronomica VARCHAR(100),
                        grupo_quimico VARCHAR(200),
                        fabricante VARCHAR(300),
                        registro_mapa VARCHAR(100),
                        formulacao VARCHAR(100),
                        dose_min FLOAT,
                        dose_max FLOAT,
                        unidade VARCHAR(50),
                        vol_calda_min FLOAT,
                        vol_calda_max FLOAT,
                        intervalo_seguranca INTEGER,
                        periodo_carencia INTEGER,
                        classe_toxicologica VARCHAR(50),
                        classe_ambiental VARCHAR(50),
                        epi_obrigatorio TEXT,
                        restricoes TEXT,
                        modo_acao VARCHAR(300),
                        ativo BOOLEAN DEFAULT TRUE
                    )""",
                    """CREATE TABLE IF NOT EXISTS produto_cultura (
                        id SERIAL PRIMARY KEY,
                        produto_id INTEGER REFERENCES produtos_agricolas(id) ON DELETE CASCADE,
                        cultura_id INTEGER REFERENCES culturas(id) ON DELETE CASCADE,
                        compatibilidade VARCHAR(10) DEFAULT 'NAO',
                        motivo TEXT,
                        dose_recomendada VARCHAR(100),
                        dose_maxima VARCHAR(100),
                        observacoes TEXT
                    )""",
                    """CREATE TABLE IF NOT EXISTS receituarios (
                        id SERIAL PRIMARY KEY,
                        numero VARCHAR(50) UNIQUE NOT NULL,
                        nome_produtor VARCHAR(300) NOT NULL,
                        cpf_cnpj_produtor VARCHAR(30),
                        telefone_produtor VARCHAR(30),
                        nome_propriedade VARCHAR(300),
                        municipio VARCHAR(200),
                        estado VARCHAR(2),
                        area_ha FLOAT,
                        talhao VARCHAR(200),
                        car VARCHAR(100),
                        responsavel_tecnico VARCHAR(300),
                        crea_cfta VARCHAR(100),
                        cpf_rt VARCHAR(30),
                        email_rt VARCHAR(200),
                        telefone_rt VARCHAR(30),
                        cultura_id INTEGER REFERENCES culturas(id),
                        diagnostico TEXT,
                        praga_alvo VARCHAR(500),
                        estagio_fenologico VARCHAR(300),
                        nivel_acao VARCHAR(200),
                        tipo_equipamento VARCHAR(200),
                        volume_calda FLOAT,
                        num_aplicacoes INTEGER DEFAULT 1,
                        intervalo_aplicacoes INTEGER,
                        epoca_aplicacao VARCHAR(300),
                        observacoes_aplicacao TEXT,
                        status VARCHAR(20) DEFAULT 'rascunho',
                        criado_por_user INTEGER,
                        criado_por_func INTEGER,
                        data_criacao TIMESTAMP DEFAULT NOW(),
                        data_emissao TIMESTAMP,
                        data_validade DATE,
                        observacoes TEXT
                    )""",
                    """CREATE TABLE IF NOT EXISTS itens_receituario (
                        id SERIAL PRIMARY KEY,
                        receituario_id INTEGER REFERENCES receituarios(id) ON DELETE CASCADE,
                        produto_id INTEGER REFERENCES produtos_agricolas(id),
                        dose FLOAT,
                        unidade VARCHAR(50),
                        volume_calda FLOAT,
                        num_aplicacoes INTEGER DEFAULT 1,
                        status_validacao VARCHAR(10),
                        motivo_restricao TEXT,
                        observacoes TEXT
                    )""",
                    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS foto_url TEXT",
                    "ALTER TABLE employees ADD COLUMN IF NOT EXISTS acesso_gis BOOLEAN NOT NULL DEFAULT FALSE",
                    "ALTER TABLE employee_files ADD COLUMN IF NOT EXISTS cloudinary_url TEXT",
                    "ALTER TABLE employee_files ADD COLUMN IF NOT EXISTS cloudinary_public_id VARCHAR(255)",
                    "ALTER TABLE employee_files ADD COLUMN IF NOT EXISTS file_size INTEGER",
                    """CREATE TABLE IF NOT EXISTS posts (
                        id SERIAL PRIMARY KEY,
                        titulo VARCHAR(200) NOT NULL,
                        descricao TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        ativo BOOLEAN DEFAULT TRUE
                    )""",
                    """CREATE TABLE IF NOT EXISTS post_midias (
                        id SERIAL PRIMARY KEY,
                        post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
                        tipo VARCHAR(10) NOT NULL,
                        url TEXT NOT NULL,
                        public_id VARCHAR(255),
                        ordem INTEGER DEFAULT 0
                    )""",
                    "ALTER TABLE post_midias ALTER COLUMN tipo TYPE VARCHAR(20)",
                    "ALTER TABLE talhoes ADD COLUMN IF NOT EXISTS data_voo DATE",
                    "ALTER TABLE talhoes ADD COLUMN IF NOT EXISTS pista_voo VARCHAR(200)",
                    """CREATE TABLE IF NOT EXISTS talhoes (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        nome VARCHAR(200) NOT NULL,
                        cultura VARCHAR(100),
                        area_ha FLOAT,
                        geojson TEXT NOT NULL,
                        cor VARCHAR(20) DEFAULT '#22c55e',
                        observacoes TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )""",
                    """CREATE TABLE IF NOT EXISTS solicitacoes_aplicacao (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                        talhao_id INTEGER REFERENCES talhoes(id) ON DELETE CASCADE,
                        cultura VARCHAR(100),
                        produto VARCHAR(200),
                        dose VARCHAR(100),
                        data_desejada DATE,
                        observacoes TEXT,
                        status VARCHAR(30) DEFAULT 'pendente',
                        resposta_admin TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )""",
                ]
                for _sql in _migrations:
                    try:
                        _conn.execute(_text(_sql))
                        _conn.commit()
                    except Exception:
                        _conn.rollback()
        except Exception:
            pass
        # ── Fim migration ──

        # Admin cliente padrão
        if not User.query.filter_by(email="admin@teste.com").first():
            admin_user = User(
                name="Admin",
                email="admin@teste.com",
                password_hash=generate_password_hash("123456"),
                is_admin=True,
            )
            db.session.add(admin_user)
            db.session.commit()


        # Seed da equipe (só cria se não existir nenhum membro)
        from app.models.team_member import TeamMember
        if TeamMember.query.count() == 0:
            membros_padrao = [
                TeamMember(nome="Weikren", cargo="Diretor de Operações", setor="Diretoria",
                           tags="Gestão,Segurança Operacional",
                           descricao="Responsável pela gestão das operações aéreas, padronização de processos, planejamento e relacionamento com clientes.",
                           ordem=1),
                TeamMember(nome="Coordenador / Piloto 01", cargo="Coordenador", setor="Coordenação & Pilotos",
                           tags="Planejamento,Briefing",
                           descricao="Coordena equipes em campo, organiza programação, checklist, rota e apoio operacional.",
                           ordem=1),
                TeamMember(nome="Coordenador / Piloto 02", cargo="Coordenador", setor="Coordenação & Pilotos",
                           tags="Execução,Qualidade",
                           descricao="Responsável por alinhamento técnico, padrão de aplicação e suporte ao time de pilotos.",
                           ordem=2),
                TeamMember(nome="Piloto Agrícola 01", cargo="Aplicação Aérea", setor="Pilotos Agrícolas",
                           tags="Precisão,Segurança",
                           descricao="Execução de aplicações com foco em uniformidade, cobertura e segurança operacional.",
                           ordem=1),
                TeamMember(nome="Piloto Agrícola 02", cargo="Aplicação Aérea", setor="Pilotos Agrícolas",
                           tags="Eficiência,Conformidade",
                           descricao="Operação e execução com padrão de qualidade e rastreabilidade.",
                           ordem=2),
                TeamMember(nome="Piloto Agrícola 03", cargo="Aplicação Aérea", setor="Pilotos Agrícolas",
                           tags="Qualidade,Rotas",
                           descricao="Aplicações com precisão, atenção ao vento, faixa e padronização.",
                           ordem=3),
                TeamMember(nome="Piloto Agrícola 04", cargo="Aplicação Aérea", setor="Pilotos Agrícolas",
                           tags="Performance,Segurança",
                           descricao="Execução com alto padrão operacional e segurança.",
                           ordem=4),
                TeamMember(nome="Piloto Agrícola 05", cargo="Aplicação Aérea", setor="Pilotos Agrícolas",
                           tags="Cobertura,Precisão",
                           descricao="Aplicações com foco em cobertura, faixa e consistência.",
                           ordem=5),
                TeamMember(nome="Analista", cargo="Análise Operacional", setor="Tecnologia & Análise",
                           tags="Mapas,Relatórios",
                           descricao="Responsável por análises, relatórios, mapas e indicadores para melhorar desempenho e qualidade.",
                           ordem=1),
                TeamMember(nome="Comercial", cargo="Atendimento & Negócios", setor="Comercial",
                           tags="Propostas,Pós-venda",
                           descricao="Atendimento, propostas e acompanhamento para garantir agilidade e clareza no serviço.",
                           ordem=1),
            ]
            for m in membros_padrao:
                db.session.add(m)
            db.session.commit()

        # Admin funcionário padrão
        if not Employee.query.filter_by(username="admin123").first():
            admin_employee = Employee(
                name="Admin",
                username="admin123",
                password_hash=generate_password_hash("123456"),
                is_admin=True,
            )
            db.session.add(admin_employee)
            db.session.commit()

        # Seed Receituário Agronômico (culturas + produtos locais)
        try:
            from app.models.receituario import (seed_receituario, seed_produtos,
                                                 seed_produtos_novos)
            seed_receituario()
            seed_produtos()
            seed_produtos_novos()  # adiciona produtos novos sem apagar existentes
        except Exception as _se:
            pass

    # Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.employee import employee_bp
    from app.routes.posts import posts_bp
    from app.routes.talhoes import talhoes_bp
    from app.routes.receituario import receituario_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(posts_bp)
    app.register_blueprint(talhoes_bp)
    app.register_blueprint(receituario_bp)

    # Context: current_user (cliente)
    from app.utils.security import get_current_user, get_current_employee

    @app.context_processor
    def inject_user():
        return {
            "current_user": get_current_user(),
            "user": get_current_user(),
            "current_employee": get_current_employee(),
        }

    return app
