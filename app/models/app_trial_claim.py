from datetime import datetime

from app import db


class AppTrialClaim(db.Model):
    """Registro mínimo e persistente do teste Premium do aplicativo móvel.

    O e-mail nunca é salvo nesta tabela. `email_hash` recebe um HMAC-SHA256
    calculado no servidor usando a SECRET_KEY do Railway. Isso permite reconhecer
    o mesmo e-mail após exclusão/recriação da conta sem manter o endereço em
    texto puro.
    """

    __tablename__ = "app_trial_claims"

    id = db.Column(db.Integer, primary_key=True)
    email_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    started_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<AppTrialClaim {self.email_hash[:10]}...>"
