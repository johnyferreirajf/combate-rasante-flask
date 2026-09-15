"""API mínima usada pelo aplicativo móvel Combate Rasante.

A autenticação desta API é feita com o Firebase ID Token enviado pelo app.
O backend valida o token diretamente na API oficial do Firebase Authentication,
sem confiar em e-mail ou UID enviados pelo cliente.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac

import requests
from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db
from app.models.app_trial_claim import AppTrialClaim


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

    email_hash = _trial_email_hash(identity["email"])
    now = datetime.utcnow()

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
