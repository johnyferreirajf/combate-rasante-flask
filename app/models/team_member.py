from datetime import datetime
from app import db


class TeamMember(db.Model):
    __tablename__ = "team_members"

    id          = db.Column(db.Integer, primary_key=True)
    nome        = db.Column(db.String(120), nullable=False)
    cargo       = db.Column(db.String(120), nullable=False)   # tag principal (verde)
    setor       = db.Column(db.String(80),  nullable=False)   # grupo/divider
    tags        = db.Column(db.String(255), default="")       # tags extras sep por vírgula
    descricao   = db.Column(db.Text,        default="")
    ordem       = db.Column(db.Integer,     default=0)        # ordem dentro do setor

    # Foto
    foto_url    = db.Column(db.Text,        default="")
    foto_public_id = db.Column(db.String(255), default="")

    ativo       = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<TeamMember {self.nome}>"

    @property
    def tags_list(self):
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def avatar_letra(self):
        return (self.nome or "?")[:2].upper()
