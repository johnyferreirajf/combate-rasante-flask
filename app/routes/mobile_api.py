"""API mínima usada pelo aplicativo móvel Combate Rasante.

A autenticação desta API é feita com o Firebase ID Token enviado pelo app.
O backend valida o token diretamente na API oficial do Firebase Authentication,
sem confiar em e-mail ou UID enviados pelo cliente.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os

import requests
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.app_trial_claim import AppTrialClaim
from app.models.app_subscription import AppSubscription
from app.services.google_play import (
    GooglePlayApiError,
    GooglePlayConfigError,
    acknowledge_subscription,
    get_subscription,
    subscription_snapshot,
)


mobile_api_bp = Blueprint("mobile_api", __name__, url_prefix="/api/app")

FIREBASE_ACCOUNTS_LOOKUP = (
    "https://identitytoolkit.googleapis.com/v1/accounts:lookup"
)
TRIAL_DAYS = 7


def _utc_iso(value: datetime) -> str:
    """Serializa datetime ingênuo do banco explicitamente como UTC."""
    return value.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_client_utc(value):
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except (TypeError, ValueError):
        return None


def _bearer_token() -> str | None:
    header = (request.headers.get("Authorization") or "").strip()
    if not header.lower().startswith("bearer "):
        return None
    token = header[7:].strip()
    return token or None


def _firebase_identity(id_token: str):
    """Valida ID token no Firebase e retorna a identidade autenticada.

    A API key do Firebase identifica o projeto; ela não substitui o ID token do
    usuário. O endereço de e-mail usado para o trial vem exclusivamente da
    resposta validada do Firebase.
    """
    api_key = current_app.config.get("FIREBASE_WEB_API_KEY")
    if not api_key:
        current_app.logger.error("FIREBASE_WEB_API_KEY não configurada")
        return None, (jsonify({"ok": False, "error": "server_config"}), 503)

    try:
        response = requests.post(
            FIREBASE_ACCOUNTS_LOOKUP,
            params={"key": api_key},
            json={"idToken": id_token},
            timeout=8,
        )
    except requests.RequestException:
        current_app.logger.exception("Falha ao validar Firebase ID token")
        return None, (jsonify({"ok": False, "error": "firebase_unavailable"}), 503)

    if response.status_code != 200:
        return None, (jsonify({"ok": False, "error": "invalid_token"}), 401)

    payload = response.json() if response.content else {}
    users = payload.get("users") or []
    if not users:
        return None, (jsonify({"ok": False, "error": "invalid_token"}), 401)

    identity = users[0]
    email = (identity.get("email") or "").strip().lower()
    if not email:
        return None, (jsonify({"ok": False, "error": "email_missing"}), 401)
    if identity.get("emailVerified") is not True:
        return None, (jsonify({"ok": False, "error": "email_not_verified"}), 403)

    return identity, None


def _trial_email_hash(email: str) -> str:
    # Usa HMAC em vez de SHA puro para não manter um hash facilmente enumerável.
    secret = str(current_app.config["SECRET_KEY"]).encode("utf-8")
    normalized = email.strip().lower().encode("utf-8")
    return hmac.new(secret, b"app-trial-v1:" + normalized, hashlib.sha256).hexdigest()


def _subscription_account_hash(identity: dict) -> str:
    """Identificador interno estável da conta Firebase sem salvar o UID puro."""
    uid = str(identity.get("localId") or "").strip()
    if not uid:
        # O Firebase normalmente sempre retorna localId. O fallback usa o e-mail
        # validado para não quebrar contas antigas em respostas atípicas.
        uid = f"email:{identity['email'].strip().lower()}"
    secret = str(current_app.config["SECRET_KEY"]).encode("utf-8")
    return hmac.new(
        secret,
        b"app-subscription-account-v1:" + uid.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _subscription_email_hash(email: str) -> str:
    secret = str(current_app.config["SECRET_KEY"]).encode("utf-8")
    normalized = email.strip().lower().encode("utf-8")
    return hmac.new(
        secret,
        b"app-subscription-email-v1:" + normalized,
        hashlib.sha256,
    ).hexdigest()


def _purchase_token_hash(purchase_token: str) -> str:
    # Purchase tokens têm alta entropia; SHA-256 é adequado para busca/UNIQUE.
    return hashlib.sha256(purchase_token.encode("utf-8")).hexdigest()


def _naive_utc(value):
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _subscription_json(snapshot, *, acknowledged: bool | None = None):
    return {
        "provider": "google_play",
        "premium": snapshot.entitled,
        "productId": snapshot.product_id,
        "basePlanId": snapshot.base_plan_id,
        "subscriptionState": snapshot.subscription_state,
        "acknowledgementState": (
            "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED"
            if acknowledged is True
            else snapshot.acknowledgement_state
        ),
        "expiresAt": snapshot.expiry_iso,
        "autoRenewing": snapshot.auto_renewing,
        "testPurchase": snapshot.is_test_purchase,
    }


def _is_play_review_email(email: str) -> bool:
    """Retorna True apenas para contas explicitamente liberadas para revisão.

    A lista vem do Railway por PLAY_REVIEW_EMAIL (ou, opcionalmente,
    PLAY_REVIEW_EMAILS separado por vírgulas). O e-mail usado aqui vem do
    Firebase ID Token já validado, portanto o cliente não consegue escolher
    outro endereço para obter o benefício.
    """
    configured = []
    single = (os.environ.get("PLAY_REVIEW_EMAIL") or "").strip()
    multiple = (os.environ.get("PLAY_REVIEW_EMAILS") or "").strip()
    if single:
        configured.append(single)
    if multiple:
        configured.extend(part.strip() for part in multiple.split(","))
    allowed = {item.lower() for item in configured if item}
    return email.strip().lower() in allowed


@mobile_api_bp.get("/health")
def health():
    return jsonify({"ok": True, "service": "combate-rasante-app-api"})


@mobile_api_bp.post("/trial/claim")
def claim_trial():
    """Cria o teste apenas uma vez por e-mail e depois sempre devolve o original.

    Se a conta Firebase for apagada e o mesmo e-mail for cadastrado novamente,
    o HMAC continua igual e o período original é reaproveitado (ou permanece
    expirado). Assim, excluir/recriar a conta nunca reinicia os 7 dias.
    """
    token = _bearer_token()
    if not token:
        return jsonify({"ok": False, "error": "missing_token"}), 401

    identity, error_response = _firebase_identity(token)
    if error_response is not None:
        return error_response

    now = datetime.utcnow()

    # Conta(s) usada(s) exclusivamente pela equipe de revisão das lojas.
    # O acesso é concedido apenas após o Firebase confirmar a identidade e o
    # e-mail. Não altera nem renova o trial de usuários comuns e não depende do
    # registro em app_trial_claims.
    if _is_play_review_email(identity["email"]):
        review_end = datetime(2099, 12, 31, 23, 59, 59)
        remaining_seconds = max(0, int((review_end - now).total_seconds()))
        return jsonify(
            {
                "ok": True,
                "trialClaimed": True,
                "trialActive": True,
                "createdNow": False,
                "startedAt": _utc_iso(now),
                "endsAt": _utc_iso(review_end),
                "serverNow": _utc_iso(now),
                "remainingSeconds": remaining_seconds,
                "reviewAccess": True,
            }
        )

    email_hash = _trial_email_hash(identity["email"])

    claim = AppTrialClaim.query.filter_by(email_hash=email_hash).first()
    created_now = False

    if claim is None:
        # Migração V38 -> V39: se este aparelho já tinha um período local
        # legítimo, preservamos as datas originais na primeira sincronização
        # para não reiniciar os 7 dias apenas por causa da atualização.
        body = request.get_json(silent=True) or {}
        migration_claimed = body.get("migrationTrialClaimed") is True
        migration_start = _parse_client_utc(body.get("migrationTrialStartedAt"))
        migration_end = _parse_client_utc(body.get("migrationTrialEndsAt"))

        use_migration = False
        if migration_claimed and migration_start and migration_end:
            duration = migration_end - migration_start
            use_migration = (
                duration.total_seconds() > 0
                and duration <= timedelta(days=TRIAL_DAYS, minutes=5)
                and migration_start <= now + timedelta(minutes=5)
                and migration_end <= now + timedelta(days=TRIAL_DAYS, minutes=5)
            )

        started_at = migration_start if use_migration else now
        ends_at = migration_end if use_migration else now + timedelta(days=TRIAL_DAYS)

        claim = AppTrialClaim(
            email_hash=email_hash,
            started_at=started_at,
            ends_at=ends_at,
            last_seen_at=now,
        )
        db.session.add(claim)
        try:
            db.session.commit()
            created_now = True
        except IntegrityError:
            # Duas requisições simultâneas do mesmo e-mail: a restrição UNIQUE
            # decide qual cria; a outra apenas lê o mesmo período já persistido.
            db.session.rollback()
            claim = AppTrialClaim.query.filter_by(email_hash=email_hash).first()
            if claim is None:
                return jsonify({"ok": False, "error": "trial_persistence"}), 500
    else:
        claim.last_seen_at = now
        db.session.commit()

    active = claim.started_at <= now < claim.ends_at
    remaining_seconds = max(0, int((claim.ends_at - now).total_seconds()))

    return jsonify(
        {
            "ok": True,
            "trialClaimed": True,
            "trialActive": active,
            "createdNow": created_now,
            "startedAt": _utc_iso(claim.started_at),
            "endsAt": _utc_iso(claim.ends_at),
            "serverNow": _utc_iso(now),
            "remainingSeconds": remaining_seconds,
        }
    )

@mobile_api_bp.post("/subscription/google/verify")
def verify_google_subscription():
    """Valida uma compra Google Play e vincula o token à conta Firebase.

    O cliente envia somente o purchaseToken. Produto, pacote, estado e validade
    são aceitos exclusivamente da resposta autenticada da Google Play.
    """
    token = _bearer_token()
    if not token:
        return jsonify({"ok": False, "error": "missing_token"}), 401

    identity, error_response = _firebase_identity(token)
    if error_response is not None:
        return error_response

    body = request.get_json(silent=True) or {}
    purchase_token = body.get("purchaseToken")
    if not isinstance(purchase_token, str):
        return jsonify({"ok": False, "error": "purchase_token_missing"}), 400
    purchase_token = purchase_token.strip()
    if len(purchase_token) < 16 or len(purchase_token) > 4096:
        return jsonify({"ok": False, "error": "purchase_token_invalid"}), 400

    expected_product = current_app.config["GOOGLE_PLAY_SUBSCRIPTION_ID"]
    token_hash = _purchase_token_hash(purchase_token)
    account_hash = _subscription_account_hash(identity)
    email_hash = _subscription_email_hash(identity["email"])

    # Um mesmo purchase token não pode liberar Premium em duas contas do app.
    existing = AppSubscription.query.filter_by(purchase_token_hash=token_hash).first()
    if (
        existing is not None
        and existing.account_hash != account_hash
        and existing.email_hash != email_hash
    ):
        return jsonify({"ok": False, "error": "purchase_linked_to_another_account"}), 409

    try:
        payload = get_subscription(purchase_token)
        snapshot = subscription_snapshot(payload, expected_product)
    except GooglePlayConfigError as exc:
        current_app.logger.error("Google Play config: %s", exc)
        return jsonify({"ok": False, "error": "google_play_server_config"}), 503
    except GooglePlayApiError as exc:
        return jsonify({"ok": False, "error": exc.code}), exc.status_code
    except requests.RequestException:
        current_app.logger.exception("Falha de rede ao consultar Google Play")
        return jsonify({"ok": False, "error": "google_play_unavailable"}), 503

    # Só vinculamos tokens que realmente pertencem ao produto Premium esperado.
    now = datetime.utcnow()
    record = existing
    if record is None:
        record = AppSubscription(
            account_hash=account_hash,
            email_hash=email_hash,
            purchase_token=purchase_token,
            purchase_token_hash=token_hash,
            product_id=snapshot.product_id,
            subscription_state=snapshot.subscription_state,
            acknowledgement_state=snapshot.acknowledgement_state,
            last_verified_at=now,
        )
        db.session.add(record)

    record.account_hash = account_hash
    record.email_hash = email_hash
    record.purchase_token = purchase_token
    record.product_id = snapshot.product_id
    record.base_plan_id = snapshot.base_plan_id
    record.subscription_state = snapshot.subscription_state
    record.acknowledgement_state = snapshot.acknowledgement_state
    record.expiry_time = _naive_utc(snapshot.expiry_time)
    record.auto_renewing = snapshot.auto_renewing
    record.is_test_purchase = snapshot.is_test_purchase
    record.order_id = snapshot.order_id
    record.last_verified_at = now

    acknowledged_now = False
    # A confirmação só ocorre depois de a Google Play provar que existe direito
    # válido. Pending/on-hold/paused/expired não recebem Premium nem acknowledge.
    if (
        snapshot.entitled
        and snapshot.acknowledgement_state == "ACKNOWLEDGEMENT_STATE_PENDING"
    ):
        try:
            acknowledge_subscription(purchase_token, expected_product)
            record.acknowledgement_state = "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED"
            acknowledged_now = True
        except GooglePlayConfigError as exc:
            db.session.rollback()
            current_app.logger.error("Google Play config ao confirmar compra: %s", exc)
            return jsonify({"ok": False, "error": "google_play_server_config"}), 503
        except GooglePlayApiError as exc:
            db.session.rollback()
            return jsonify({"ok": False, "error": exc.code}), exc.status_code
        except requests.RequestException:
            db.session.rollback()
            current_app.logger.exception("Falha de rede ao confirmar compra Google Play")
            return jsonify({"ok": False, "error": "google_play_unavailable"}), 503

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # Proteção adicional contra corrida entre duas contas verificando o mesmo token.
        owner = AppSubscription.query.filter_by(purchase_token_hash=token_hash).first()
        if (
            owner is not None
            and owner.account_hash != account_hash
            and owner.email_hash != email_hash
        ):
            return jsonify({"ok": False, "error": "purchase_linked_to_another_account"}), 409
        return jsonify({"ok": False, "error": "subscription_persistence"}), 500

    data = _subscription_json(snapshot, acknowledged=(acknowledged_now or record.acknowledgement_state == "ACKNOWLEDGEMENT_STATE_ACKNOWLEDGED"))
    return jsonify({"ok": True, **data})


@mobile_api_bp.get("/subscription/google/status")
def google_subscription_status():
    """Revalida no Google Play a assinatura já vinculada à conta atual."""
    token = _bearer_token()
    if not token:
        return jsonify({"ok": False, "error": "missing_token"}), 401

    identity, error_response = _firebase_identity(token)
    if error_response is not None:
        return error_response

    account_hash = _subscription_account_hash(identity)
    email_hash = _subscription_email_hash(identity["email"])
    expected_product = current_app.config["GOOGLE_PLAY_SUBSCRIPTION_ID"]

    records = (
        AppSubscription.query.filter(
            or_(
                AppSubscription.account_hash == account_hash,
                AppSubscription.email_hash == email_hash,
            )
        )
        .order_by(AppSubscription.updated_at.desc())
        .limit(5)
        .all()
    )
    if not records:
        return jsonify({"ok": True, "provider": "google_play", "premium": False, "subscriptionState": "NONE"})

    last_non_entitled = None
    for record in records:
        try:
            payload = get_subscription(record.purchase_token)
            snapshot = subscription_snapshot(payload, expected_product)
        except GooglePlayApiError as exc:
            if exc.code in {"purchase_not_found", "purchase_expired_or_gone"}:
                record.subscription_state = "SUBSCRIPTION_STATE_EXPIRED"
                record.last_verified_at = datetime.utcnow()
                last_non_entitled = {
                    "ok": True,
                    "provider": "google_play",
                    "premium": False,
                    "subscriptionState": "SUBSCRIPTION_STATE_EXPIRED",
                }
                continue
            return jsonify({"ok": False, "error": exc.code}), exc.status_code
        except GooglePlayConfigError as exc:
            current_app.logger.error("Google Play config: %s", exc)
            return jsonify({"ok": False, "error": "google_play_server_config"}), 503
        except requests.RequestException:
            current_app.logger.exception("Falha de rede ao revalidar Google Play")
            return jsonify({"ok": False, "error": "google_play_unavailable"}), 503

        record.account_hash = account_hash
        record.email_hash = email_hash
        record.product_id = snapshot.product_id
        record.base_plan_id = snapshot.base_plan_id
        record.subscription_state = snapshot.subscription_state
        record.acknowledgement_state = snapshot.acknowledgement_state
        record.expiry_time = _naive_utc(snapshot.expiry_time)
        record.auto_renewing = snapshot.auto_renewing
        record.is_test_purchase = snapshot.is_test_purchase
        record.order_id = snapshot.order_id
        record.last_verified_at = datetime.utcnow()

        data = {"ok": True, **_subscription_json(snapshot)}
        last_non_entitled = data
        if snapshot.entitled:
            db.session.commit()
            return jsonify(data)

    db.session.commit()
    return jsonify(last_non_entitled or {"ok": True, "provider": "google_play", "premium": False, "subscriptionState": "NONE"})

