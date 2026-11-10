"""Regras de elegibilidade para assinaturas Apple verificadas pelo servidor.

Este módulo apenas avalia dados já verificados criptograficamente e o status
consultado na App Store Server API. Não consulta a Apple nem libera acesso.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

PREMIUM_PRODUCTS = frozenset({
    "combate_rasante_premium_mensal",
    "combate_rasante_premium_anual",
})

# Valores documentados pela Apple para assinaturas autorrenováveis.
ACTIVE = 1
BILLING_GRACE_PERIOD = 4


@dataclass(frozen=True)
class AppleEntitlement:
    entitled: bool
    original_transaction_id: str | None
    product_id: str | None
    expires_at: datetime | None
    state: str


def evaluate_apple_entitlement(transaction, status: int, *, now=None):
    """Avalia uma transação JWS validada, associada a um status Apple.

    O chamador DEVE obter ambos da App Store Server API para a mesma assinatura,
    verificar a assinatura JWS e conferir o vínculo da conta no banco de dados.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now deve incluir fuso horário")
    now = now.astimezone(timezone.utc)

    product_id = getattr(transaction, "productId", None)
    original_id = getattr(transaction, "originalTransactionId", None)
    expires_ms = getattr(transaction, "expiresDate", None)
    revoked_ms = getattr(transaction, "revocationDate", None)
    upgraded = getattr(transaction, "isUpgraded", None) is True

    expires_at = None
    if isinstance(expires_ms, (int, float)) and not isinstance(expires_ms, bool):
        try:
            expires_at = datetime.fromtimestamp(expires_ms / 1000, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            pass

    if product_id not in PREMIUM_PRODUCTS or not original_id:
        state = "INVALID_PRODUCT_OR_ORIGINAL_ID"
    elif revoked_ms is not None:
        state = "REVOKED"
    elif upgraded:
        state = "UPGRADED_TRANSACTION"
    elif status == BILLING_GRACE_PERIOD:
        # O período de graça exige consultar gracePeriodExpiresDate no JWS de renovação.
        # Não conceder automaticamente acesso usando expiresDate da transação anterior.
        state = "GRACE_REQUIRES_RENEWAL_INFO"
    elif status != ACTIVE:
        state = f"NOT_ENTITLED_STATUS_{status}"
    elif expires_at is None or expires_at <= now:
        state = "EXPIRED_TRANSACTION"
    else:
        state = "ACTIVE"

    return AppleEntitlement(
        entitled=state == "ACTIVE",
        original_transaction_id=str(original_id) if original_id else None,
        product_id=product_id,
        expires_at=expires_at,
        state=state,
    )
