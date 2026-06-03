from app import db
from datetime import datetime


SECOES_CARROSSEL = [
    {"slug": "clientes",   "label": "Clientes",   "icon": "👤", "default": "img/tiles/clientes.png"},
    {"slug": "atividades", "label": "Atividades", "icon": "🌿", "default": "img/tiles/atividades.png"},
    {"slug": "parceria",   "label": "Parcerias",  "icon": "🤝", "default": "img/tiles/parceria.png"},
    {"slug": "equipe",     "label": "Equipe",     "icon": "👥", "default": "img/tiles/equipe.png"},
    {"slug": "eventos",    "label": "Eventos",    "icon": "📅", "default": "img/tiles/eventos.png"},
]


class CarrosselImagem(db.Model):
    __tablename__ = "carrossel_imagens"

    id           = db.Column(db.Integer, primary_key=True)
    secao        = db.Column(db.String(50), unique=True, nullable=False)
    url          = db.Column(db.Text, nullable=False)
    public_id    = db.Column(db.String(300))
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {"secao": self.secao, "url": self.url}
