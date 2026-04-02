from datetime import datetime
from app import db

class ActionLog(db.Model):
    __tablename__ = "action_logs"

    id          = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    employee    = db.relationship("Employee", backref="action_logs")
    acao        = db.Column(db.String(50),  nullable=False)  # "excluir_arquivo", "excluir_pasta"
    detalhe     = db.Column(db.String(500), nullable=True)   # nome do arquivo/pasta
    created_at  = db.Column(db.DateTime,   default=datetime.utcnow)

    def __repr__(self):
        return f"<ActionLog {self.acao} by emp={self.employee_id}>"
