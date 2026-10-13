"""Integração segura com a Google Play Developer API.

Este módulo roda exclusivamente no backend. A chave da conta de serviço nunca
é enviada ao aplicativo Flutter.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from urllib.parse import quote

import requests
from flask import current_app
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

ANDROID_PUBLISHER_SCOPE = "https://www.googleapis.com/auth/androidpublisher"
ANDROID_PUBLISHER_BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3"


class GooglePlayConfigError(RuntimeError):
    """Configuração ausente ou inválida da conta de serviço."""


class GooglePlayApiError(RuntimeError):
    """Falha ao consultar ou atualizar a Google Play Developer API."""

    def __init__(self, code: str, status_code: int = 502):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass(frozen=True)
class SubscriptionSnapshot:
    product_id: str
    base_plan_id: str | None
    subscription_state: str
    acknowledgement_state: str
    expiry_time: datetime | None
    auto_renewing: bool
    entitled: bool
    is_test_purchase: bool
    order_id: str | None
    linked_purchase_token: str | None
    raw: dict[str, Any]

    @property
    def expiry_iso(self) -> str | None:
        if self.expiry_time is None:
            return None
        return self.expiry_time.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_rfc3339(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _service_account_info() -> dict[str, Any]:
    """Lê a credencial de Railway sem depender de arquivo local.

    Preferimos GOOGLE_PLAY_SERVICE_ACCOUNT_JSON_B64 porque evita problemas com
    quebras de linha da private_key. Também aceitamos JSON puro para ambientes
    em que a variável multilinha funciona bem.
    """
    encoded = (current_app.config.get("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON_B64") or "").strip()
    raw_json = (current_app.config.get("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON") or "").strip()

    if encoded:
        try:
            decoded = base64.b64decode(encoded).decode("utf-8")
            info = json.loads(decoded)
        except Exception as exc:  # noqa: BLE001 - converte tudo em erro de config seguro
            raise GooglePlayConfigError("invalid_service_account_b64") from exc
    elif raw_json:
        try:
            info = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise GooglePlayConfigError("invalid_service_account_json") from exc
    else:
        raise GooglePlayConfigError("service_account_missing")

    required = {"client_email", "private_key", "token_uri"}
    if not isinstance(info, dict) or not required.issubset(info):
        raise GooglePlayConfigError("service_account_incomplete")
    return info


@lru_cache(maxsize=1)
def _cached_credentials(serialized_info: str):
    info = json.loads(serialized_info)
    return service_account.Credentials.from_service_account_info(
        info,
        scopes=[ANDROID_PUBLISHER_SCOPE],
    )


def _authorized_session() -> AuthorizedSession:
    # Usar string canônica como chave do cache evita recriar o objeto a cada chamada.
    serialized = json.dumps(_service_account_info(), sort_keys=True, separators=(",", ":"))
    credentials = _cached_credentials(serialized)
    return AuthorizedSession(credentials)


def _map_http_error(response: requests.Response) -> GooglePlayApiError:
    status = response.status_code
    if status in (401, 403):
        return GooglePlayApiError("google_play_permission", 503)
    if status == 404:
        return GooglePlayApiError("purchase_not_found", 404)
    if status == 410:
        return GooglePlayApiError("purchase_expired_or_gone", 410)
    if status == 400:
        return GooglePlayApiError("google_play_invalid_purchase", 400)
    if status == 429:
        return GooglePlayApiError("google_play_rate_limited", 503)
    if status >= 500:
        return GooglePlayApiError("google_play_unavailable", 503)
    return GooglePlayApiError("google_play_api_error", 502)


def get_subscription(purchase_token: str) -> dict[str, Any]:
    package_name = current_app.config["GOOGLE_PLAY_PACKAGE_NAME"]
    token = quote(purchase_token, safe="")
    package = quote(package_name, safe="")
    url = (
        f"{ANDROID_PUBLISHER_BASE}/applications/{package}"
        f"/purchases/subscriptionsv2/tokens/{token}"
    )

    try:
        response = _authorized_session().get(url, timeout=12)
    except (requests.RequestException, GooglePlayConfigError):
        raise
    except Exception as exc:  # noqa: BLE001
        raise GooglePlayApiError("google_play_unavailable", 503) from exc

    if response.status_code != 200:
        raise _map_http_error(response)

    try:
        payload = response.json()
    except ValueError as exc:
        raise GooglePlayApiError("google_play_invalid_response", 502) from exc

    if not isinstance(payload, dict):
        raise GooglePlayApiError("google_play_invalid_response", 502)
    return payload


def acknowledge_subscription(purchase_token: str, subscription_id: str) -> None:
    """Confirma a compra inicial no backend.

    A API v2 é usada para consultar o estado, enquanto o endpoint de acknowledge
    permanece em purchases.subscriptions. Renovações já confirmadas não precisam
    ser confirmadas novamente.
    """
    package_name = current_app.config["GOOGLE_PLAY_PACKAGE_NAME"]
    token = quote(purchase_token, safe="")
    package = quote(package_name, safe="")
    product = quote(subscription_id, safe="")
    url = (
        f"{ANDROID_PUBLISHER_BASE}/applications/{package}"
        f"/purchases/subscriptions/{product}/tokens/{token}:acknowledge"
    )

    try:
        response = _authorized_session().post(url, json={}, timeout=12)
    except (requests.RequestException, GooglePlayConfigError):
        raise
    except Exception as exc:  # noqa: BLE001
        raise GooglePlayApiError("google_play_unavailable", 503) from exc

    # A API normalmente responde 200 com corpo vazio.
    if response.status_code not in (200, 204):
        raise _map_http_error(response)


def subscription_snapshot(payload: dict[str, Any], expected_product_id: str) -> SubscriptionSnapshot:
    state = str(payload.get("subscriptionState") or "SUBSCRIPTION_STATE_UNSPECIFIED")
    ack_state = str(payload.get("acknowledgementState") or "ACKNOWLEDGEMENT_STATE_UNSPECIFIED")
    line_items = payload.get("lineItems") or []

    matching_items = [
        item for item in line_items
        if isinstance(item, dict) and item.get("productId") == expected_product_id
    ]
    if not matching_items:
        raise GooglePlayApiError("wrong_subscription_product", 400)

    # Para uma assinatura comum há um item. Em transições, pode haver mais de um;
    # usamos o item do produto esperado com vencimento mais distante.
    def item_expiry(item: dict[str, Any]) -> datetime:
        return _parse_rfc3339(item.get("expiryTime")) or datetime.min.replace(tzinfo=timezone.utc)

    item = max(matching_items, key=item_expiry)
    expiry = _parse_rfc3339(item.get("expiryTime"))
    now = datetime.now(timezone.utc)

    base_plan_id = None
    offer_details = item.get("offerDetails")
    if isinstance(offer_details, dict):
        raw_base_plan = offer_details.get("basePlanId")
        if raw_base_plan:
            base_plan_id = str(raw_base_plan)

    auto_renewing_plan = item.get("autoRenewingPlan")
    auto_renewing = bool(
        isinstance(auto_renewing_plan, dict)
        and auto_renewing_plan.get("autoRenewEnabled") is True
    )

    # Google documenta que cancelada ainda mantém acesso até expiryTime.
    state_allows_entitlement = state in {
        "SUBSCRIPTION_STATE_ACTIVE",
        "SUBSCRIPTION_STATE_IN_GRACE_PERIOD",
        "SUBSCRIPTION_STATE_CANCELED",
    }
    entitled = bool(
        state_allows_entitlement
        and expiry is not None
        and expiry > now
    )

    order_id = item.get("latestSuccessfulOrderId") or payload.get("latestOrderId")
    return SubscriptionSnapshot(
        product_id=expected_product_id,
        base_plan_id=base_plan_id,
        subscription_state=state,
        acknowledgement_state=ack_state,
        expiry_time=expiry,
        auto_renewing=auto_renewing,
        entitled=entitled,
        is_test_purchase=isinstance(payload.get("testPurchase"), dict),
        order_id=str(order_id) if order_id else None,
        linked_purchase_token=(str(payload.get("linkedPurchaseToken")) if payload.get("linkedPurchaseToken") else None),
        raw=payload,
    )
