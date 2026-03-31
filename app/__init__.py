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

    # Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.employee import employee_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)

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
