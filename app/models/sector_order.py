from app import db

class SectorOrder(db.Model):
    __tablename__ = "sector_orders"
    id       = db.Column(db.Integer, primary_key=True)
    setor    = db.Column(db.String(120), unique=True, nullable=False)
    posicao  = db.Column(db.Integer, default=99)

    def __repr__(self):
        return f"<SectorOrder {self.setor} pos={self.posicao}>"
