"""
client_file.py
Modelo para arquivos dos clientes — substitui o sistema de pastas fixas (tema/safra/mes/dia)
por uma estrutura de pastas livre, igual ao portal de funcionários.
"""
from datetime import datetime
from app import db


class ClientFile(db.Model):
    __tablename__ = "client_files"

    id                = db.Column(db.Integer, primary_key=True)

    # ── Vínculo com o cliente ──────────────────────────────────
    user_id           = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user              = db.relationship("User", backref="client_files")

    # ── Arquivo ───────────────────────────────────────────────
    original_filename = db.Column(db.String(255), nullable=False)
    title             = db.Column(db.String(255))          # nome exibido
    description       = db.Column(db.Text)

    # ── Pasta virtual (caminho relativo dentro do espaço do cliente) ──
    # Ex: "Safra2025-2026/Janeiro/14" ou "" para raiz
    folder_path       = db.Column(db.String(500), default="")

    # ── Storage ───────────────────────────────────────────────
    url               = db.Column(db.Text, nullable=False)
    public_id         = db.Column(db.String(255))          # ID Cloudinary
    source            = db.Column(db.String(20), default="cloudinary")
    file_size         = db.Column(db.Integer)              # bytes

    # ── Tipo ──────────────────────────────────────────────────
    file_ext          = db.Column(db.String(20))           # jpg, pdf, kml...

    # ── Datas ─────────────────────────────────────────────────
    uploaded_at       = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ClientFile {self.original_filename} user={self.user_id}>"

    @property
    def display_name(self):
        return self.title or self.original_filename

    @property
    def is_image(self):
        return self.file_ext and self.file_ext.lower() in {"jpg","jpeg","png","webp","gif","bmp","svg"}

    @property
    def is_pdf(self):
        return self.file_ext and self.file_ext.lower() == "pdf"

    @property
    def size_human(self):
        s = self.file_size or 0
        for unit in ["B","KB","MB","GB"]:
            if s < 1024:
                return f"{s:.1f} {unit}"
            s /= 1024
        return f"{s:.1f} GB"
