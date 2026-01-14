from datetime import datetime
from app import db


class Photo(db.Model):
    __tablename__ = "photos"
    __table_args__ = {"extend_existing": True}  # <– linha nova

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    title = db.Column(db.String(120))
    description = db.Column(db.Text)

    # data referente à operação / dia da aplicação
    taken_at = db.Column(db.Date, nullable=False)

    # data e hora em que a foto foi cadastrada no sistema
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
