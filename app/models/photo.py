from datetime import datetime
from app import db


class Photo(db.Model):
    __tablename__ = "photos"
    __table_args__ = {"extend_existing": True}

    id          = db.Column(db.Integer, primary_key=True)

    # ── Vínculo com o cliente ──────────────────────────────────
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user        = db.relationship("User", backref="photos")

    # ── Metadados do arquivo ───────────────────────────────────
    filename    = db.Column(db.String(255), nullable=False)
    title       = db.Column(db.String(120))
    description = db.Column(db.Text)

    # ── Organização (equivale a pasta: tema/safra/mes/dia) ─────
    tema        = db.Column(db.String(60),  nullable=False, default="aplicacoes")
    safra       = db.Column(db.String(60),  nullable=False, default="")
    mes         = db.Column(db.String(30),  nullable=False, default="")
    dia         = db.Column(db.String(5),   nullable=False, default="")

    # ── URL de acesso (Cloudinary ou local) ───────────────────
    url         = db.Column(db.Text, nullable=False)
    public_id   = db.Column(db.String(255))   # ID no Cloudinary para exclusão
    source      = db.Column(db.String(20), default="local")  # "cloudinary" | "local"

    # ── Datas ─────────────────────────────────────────────────
    taken_at    = db.Column(db.Date,     nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Photo {self.filename} user={self.user_id}>"
