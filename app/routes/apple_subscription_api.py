"""Rotas Apple Premium do Combate Rasante (integração em desenvolvimento).

Segurança: transações verificadas pela Apple, appAccountToken vinculado ao
Firebase UID, originalTransactionId exclusivo e estado sempre revalidado.
Não registrar este blueprint em produção antes dos testes de integração.
"""

from datetime import datetime, timezone
import hashlib
import hmac
import uuid

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError
from appstoreserverlibrary.api_client import APIException

from app import db
from app.models.app_subscription import AppSubscription
from app.routes.mobile_api import (
    _bearer_token,
    _firebase_identity,
    _subscription_account_hash,
    _subscription_email_hash,
)
from app.services.apple_entitlement import evaluate_apple_entitlement, PREMIUM_PRODUCTS
from app.services.apple_store import (
    AppleStoreConfigError,
    fetch_verified_subscription_status,
)

apple_subscription_bp = Blueprint(
    "apple_subscription", __name__, url_prefix="/api/app/subscription/apple"
)


def _identity():
    token = _bearer_token()
    if not token:
        return None, (jsonify({"ok": False, "error": "missing_token"}), 401)
    return _firebase_identity(token)


def _account_token(identity):
    """UUID determinístico e privado para StoreKit appAccountToken.

    NÃO usa email; troca de conta Firebase significa outro identificador.
    IMPORTANTE: SECRET_KEY deve ser forte, estável e exclusiva do servidor.
    """
    secret = str(current_app.config["SECRET_KEY"])
    if secret == "dev_key_change_me" or len(secret) < 32:
        raise AppleStoreConfigError("SECRET_KEY insegura para vincular Apple")
    uid = str(identity.get("localId") or "")
    if not uid:
        raise AppleStoreConfigError("Firebase UID ausente")
    digest = hmac.new(
        secret.encode("utf-8"), b"apple-app-account-v1:" + uid.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return str(uuid.UUID(bytes=digest[:16], version=4))


def _apple_token_hash(original_id):
    return hashlib.sha256(f"apple:{original_id}".encode("utf-8")).hexdigest()


def _retrieve(transaction_id):
    """Tenta produção; apenas transação inexistente pode fazer fallback Sandbox."""
    try:
        return fetch_verified_subscription_status(transaction_id, sandbox=False), False
    except APIException as exc:
        # Transação de sandbox não aparece no ambiente de produção.
        if getattr(exc, "http_status_code", None) != 404:
            raise
        return fetch_verified_subscription_status(transaction_id, sandbox=True), True


def _snapshot(initial, items, identity):
    original = str(getattr(initial, "originalTransactionId", "") or "")
    expected_account_token = _account_token(identity)
    if str(getattr(initial, "appAccountToken", "") or "").lower() != expected_account_token:
        raise PermissionError("transaction_account_mismatch")

    evaluations = []
    for status, transaction, renewal in items:
        if str(getattr(transaction, "originalTransactionId", "") or "") != original:
            raise ValueError("original_transaction_mismatch")
        if str(getattr(transaction, "appAccountToken", "") or "").lower() != expected_account_token:
            raise PermissionError("transaction_account_mismatch")
        if getattr(transaction, "productId", None) not in PREMIUM_PRODUCTS:
            continue
        evaluations.append(evaluate_apple_entitlement(transaction, status))

    if not evaluations:
        raise ValueError("apple_subscription_product_not_found")
    active = [e for e in evaluations if e.entitled]
    if active:
        return max(active, key=lambda e: e.expires_at), original
    return max(evaluations, key=lambda e: e.expires_at.timestamp() if e.expires_at else 0), original


def _result(snapshot, sandbox):
    return {
        "ok": True,
        "provider": "app_store",
        "premium": snapshot.entitled,
        "productId": snapshot.product_id,
        "subscriptionState": snapshot.state,
        "expiresAt": snapshot.expires_at.isoformat() if snapshot.expires_at else None,
        "testPurchase": sandbox,
    }


def _store_record(identity, snapshot, original_id, sandbox, existing):
    now = datetime.utcnow()
    if existing is None:
        existing = AppSubscription(
            account_hash=_subscription_account_hash(identity),
            email_hash=_subscription_email_hash(identity["email"]),
            purchase_token=f"apple:{original_id}",
            purchase_token_hash=_apple_token_hash(original_id),
            original_transaction_id=original_id,
            provider="app_store",
            product_id=snapshot.product_id,
            subscription_state=snapshot.state,
        )
        db.session.add(existing)
    existing.provider = "app_store"
    existing.product_id = snapshot.product_id
    existing.subscription_state = snapshot.state
    existing.expiry_time = (snapshot.expires_at.astimezone(timezone.utc).replace(tzinfo=None)
                            if snapshot.expires_at else None)
    existing.is_test_purchase = sandbox
    existing.last_verified_at = now
    return existing


def _existing_owned(original_id, identity):
    record = AppSubscription.query.filter_by(original_transaction_id=original_id).first()
    if record and (record.provider != "app_store" or
                   record.account_hash != _subscription_account_hash(identity)):
        raise PermissionError("purchase_linked_to_another_account")
    return record


def _server_error(exc):
    current_app.logger.warning("Apple subscription verification failed: %s", type(exc).__name__)
    if isinstance(exc, AppleStoreConfigError):
        return jsonify({"ok": False, "error": "apple_server_config"}), 503
    if isinstance(exc, PermissionError):
        return jsonify({"ok": False, "error": str(exc)}), 409
    if isinstance(exc, ValueError):
        return jsonify({"ok": False, "error": "apple_invalid_transaction"}), 422
    return jsonify({"ok": False, "error": "apple_unavailable"}), 503


@apple_subscription_bp.get("/account-token")
def apple_account_token():
    """Flutter usará esse UUID como appAccountToken na compra StoreKit 2."""
    identity, error = _identity()
    if error is not None:
        return error
    try:
        return jsonify({"ok": True, "appAccountToken": _account_token(identity)})
    except AppleStoreConfigError as exc:
        return _server_error(exc)


@apple_subscription_bp.post("/verify")
def verify_apple_subscription():
    identity, error = _identity()
    if error is not None:
        return error
    body = request.get_json(silent=True) or {}
    tid = body.get("transactionId")
    if not isinstance(tid, str) or not tid.isascii() or not tid.isdigit() or len(tid) > 128:
        return jsonify({"ok": False, "error": "transaction_id_invalid"}), 400
    try:
        (initial, items), sandbox = _retrieve(tid)
        snapshot, original = _snapshot(initial, items, identity)
        existing = _existing_owned(original, identity)
        _store_record(identity, snapshot, original, sandbox, existing)
        db.session.commit()
        return jsonify(_result(snapshot, sandbox))
    except IntegrityError:
        db.session.rollback()
        return jsonify({"ok": False, "error": "purchase_linked_to_another_account"}), 409
    except Exception as exc:
        db.session.rollback()
        return _server_error(exc)


@apple_subscription_bp.get("/status")
def apple_subscription_status():
    identity, error = _identity()
    if error is not None:
        return error
    records = (AppSubscription.query.filter_by(
        provider="app_store", account_hash=_subscription_account_hash(identity)
    ).order_by(AppSubscription.updated_at.desc()).limit(10).all())
    if not records:
        return jsonify({"ok": True, "provider": "app_store", "premium": False,
                        "subscriptionState": "NONE"})

    latest = None
    for record in records:
        try:
            (initial, items), sandbox = _retrieve(record.original_transaction_id)
            snapshot, original = _snapshot(initial, items, identity)
            if original != record.original_transaction_id:
                raise ValueError("original_transaction_mismatch")
            _store_record(identity, snapshot, original, sandbox, record)
            result = _result(snapshot, sandbox)
            latest = result
            if snapshot.entitled:
                db.session.commit()
                return jsonify(result)
        except Exception as exc:
            db.session.rollback()
            return _server_error(exc)
    db.session.commit()
    return jsonify(latest)
