"""
talhao.py — Modelos para talhões e solicitações de aplicação.
"""
from datetime import datetime
from app import db


class Talhao(db.Model):
    __tablename__ = "talhoes"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user        = db.relationship("User", backref="talhoes")

    nome        = db.Column(db.String(200), nullable=False)
    cultura     = db.Column(db.String(100))
    area_ha     = db.Column(db.Float)
    geojson     = db.Column(db.Text, nullable=False)
    cor         = db.Column(db.String(20), default="#22c55e")
    observacoes = db.Column(db.Text)

    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    solicitacoes = db.relationship("SolicitacaoAplicacao",
                                   backref="talhao",
                                   cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Talhao {self.nome} user={self.user_id}>"


class SolicitacaoAplicacao(db.Model):
    __tablename__ = "solicitacoes_aplicacao"

    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user          = db.relationship("User", backref="solicitacoes")
    talhao_id     = db.Column(db.Integer, db.ForeignKey("talhoes.id"), nullable=False)

    cultura       = db.Column(db.String(100))
    produto       = db.Column(db.String(200))
    dose          = db.Column(db.String(100))
    data_desejada = db.Column(db.Date)
    observacoes   = db.Column(db.Text)

    status        = db.Column(db.String(30), default="pendente")
    resposta_admin = db.Column(db.Text)

    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    STATUS_LABELS = {
        "pendente":   ("⏳ Aguardando análise", "#f59e0b"),
        "em_analise": ("🔍 Em análise",         "#3b82f6"),
        "aprovada":   ("✅ Aprovada",            "#22c55e"),
        "agendada":   ("📅 Agendada",            "#8b5cf6"),
        "concluida":  ("🏁 Concluída",           "#10b981"),
        "cancelada":  ("❌ Cancelada",           "#ef4444"),
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status, "#888"))

    def __repr__(self):
        return f"<Solicitacao {self.id} status={self.status}>"
