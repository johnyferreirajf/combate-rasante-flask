from datetime import datetime

from app import db


class AppSubscription(db.Model):
    """Vínculo de assinaturas Google Play ou App Store com uma conta Firebase.

    Os hashes de conta/e-mail não armazenam os identificadores em texto puro.
    O token Google Play permanece no servidor para revalidar o direito.
    No caso da Apple, o originalTransactionId identifica a cadeia de renovações;
    o tratamento de transações e seus dados assinados ocorre em serviço próprio.

    ATENÇÃO: adicionar original_transaction_id ao modelo exige migração do
    banco existente ANTES de implantar a versão atualizada do backend.
    """

    __tablename__ = "app_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    account_hash = db.Column(db.String(64), nullable=False, index=True)
    email_hash = db.Column(db.String(64), nullable=False, index=True)

    # Mantidos para compatibilidade com assinaturas Google Play já existentes.
    purchase_token = db.Column(db.Text, nullable=False)
    purchase_token_hash = db.Column(
        db.String(64), unique=True, nullable=False, index=True
    )

    # Apple: identificador estável entre renovações da mesma assinatura.
    # NULL para registros existentes do Google Play.
    original_transaction_id = db.Column(
        db.String(128), nullable=True, unique=True, index=True
    )

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
    last_verified_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow
    )

    def __repr__(self):
        return (
            f"<AppSubscription {self.provider}:"
            f"{self.product_id} {self.subscription_state}>"
        )
