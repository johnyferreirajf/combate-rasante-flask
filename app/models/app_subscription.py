from datetime import datetime

from app import db


class AppSubscription(db.Model):
    """Vínculo de uma assinatura Google Play com a conta autenticada no app.

    O e-mail e o Firebase UID não são salvos em texto puro. O purchase token é
    mantido apenas no servidor porque ele é necessário para consultar novamente
    o estado oficial da assinatura na Google Play.
    """

    __tablename__ = "app_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    account_hash = db.Column(db.String(64), nullable=False, index=True)
    email_hash = db.Column(db.String(64), nullable=False, index=True)

    purchase_token = db.Column(db.Text, nullable=False)
    purchase_token_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)

    provider = db.Column(db.String(30), nullable=False, default="google_play")
    product_id = db.Column(db.String(150), nullable=False)
    base_plan_id = db.Column(db.String(150), nullable=True)
    subscription_state = db.Column(db.String(80), nullable=False)
    acknowledgement_state = db.Column(db.String(80), nullable=True)
    expiry_time = db.Column(db.DateTime, nullable=True)
    auto_renewing = db.Column(db.Boolean, nullable=False, default=False)
    is_test_purchase = db.Column(db.Boolean, nullable=False, default=False)
    order_id = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    last_verified_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<AppSubscription {self.provider}:{self.product_id} {self.subscription_state}>"
