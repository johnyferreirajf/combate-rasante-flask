"""Cliente Apple App Store Server API para o Combate Rasante.

Este módulo NÃO concede Premium por si só. Os endpoints deverão validar o
produto, a expiração, o estado de revogação e o vínculo da transação com a
conta Firebase antes de alterar direitos de acesso.

Variáveis de ambiente no servidor (nunca no GitHub):
  APPLE_KEY_ID, APPLE_ISSUER_ID, APPLE_PRIVATE_KEY
  APPLE_ROOT_CERTIFICATES_DIR (diretório com raízes Apple confiáveis .cer/.pem)
"""

from pathlib import Path

from flask import current_app
from appstoreserverlibrary.api_client import AppStoreServerAPIClient
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier


class AppleStoreConfigError(RuntimeError):
    """Configuração necessária para consultar/verificar a Apple ausente."""


def _required_config(key: str) -> str:
    value = str(current_app.config.get(key) or "").strip()
    if not value:
        raise AppleStoreConfigError(f"Configuração Apple ausente: {key}")
    return value


def _private_key_bytes() -> bytes:
    key = _required_config("APPLE_PRIVATE_KEY").replace("\\n", "\n")
    if "BEGIN PRIVATE KEY" not in key or "END PRIVATE KEY" not in key:
        raise AppleStoreConfigError("APPLE_PRIVATE_KEY não tem formato PEM .p8")
    return key.encode("utf-8")


def _environment(sandbox: bool) -> Environment:
    return Environment.SANDBOX if sandbox else Environment.PRODUCTION


def make_api_client(*, sandbox: bool = False) -> AppStoreServerAPIClient:
    """Cria cliente autenticado; nenhuma solicitação é feita na construção."""
    return AppStoreServerAPIClient(
        _private_key_bytes(),
        _required_config("APPLE_KEY_ID"),
        _required_config("APPLE_ISSUER_ID"),
        _required_config("APPLE_BUNDLE_ID"),
        _environment(sandbox),
    )


def _trusted_apple_roots() -> list[bytes]:
    """Carrega apenas certificados raiz instalados pelo administrador.

    Não lê arquivos fornecidos pelo cliente e não baixa certificados da rede.
    Os certificados devem vir do site Apple PKI e ser conferidos antes do deploy.
    """
    directory = _required_config("APPLE_ROOT_CERTIFICATES_DIR")
    root_dir = Path(directory).resolve()
    if not root_dir.is_dir():
        raise AppleStoreConfigError("Diretório de certificados Apple não existe")
    paths = sorted(
        path for path in root_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".cer", ".der", ".pem"}
    )
    if not paths:
        raise AppleStoreConfigError("Nenhum certificado raiz Apple configurado")
    return [path.read_bytes() for path in paths]


def make_signed_data_verifier(*, sandbox: bool = False) -> SignedDataVerifier:
    """Verifica assinaturas JWS e vínculo ao aplicativo e ambiente Apple."""
    apple_id = None if sandbox else int(_required_config("APPLE_APP_ID"))
    return SignedDataVerifier(
        _trusted_apple_roots(),
        True,  # Verificações online de cadeia de certificação.
        _environment(sandbox),
        _required_config("APPLE_BUNDLE_ID"),
        apple_id,
    )


def _validate_transaction_id(transaction_id: str) -> str:
    tid = str(transaction_id or "").strip()
    if not tid or len(tid) > 128 or not tid.isascii() or not tid.isdigit():
        raise ValueError("Identificador de transação Apple inválido")
    return tid


def fetch_verified_transaction(transaction_id: str, *, sandbox: bool = False):
    """Consulta a Apple e verifica a assinatura da transação devolvida.

    NÃO implica assinatura ativa: a camada de negócio deve examinar
    productId, expiresDate, revocationDate e os demais campos de elegibilidade.
    """
    tid = _validate_transaction_id(transaction_id)
    client = make_api_client(sandbox=sandbox)
    response = client.get_transaction_info(tid)
    signed_transaction = response.signedTransactionInfo
    if not signed_transaction:
        raise ValueError("Apple não retornou transação assinada")
    verifier = make_signed_data_verifier(sandbox=sandbox)
    return verifier.verify_and_decode_signed_transaction(signed_transaction)


def fetch_verified_subscription_status(transaction_id: str, *, sandbox: bool = False):
    """Obtém estado atual e JWS verificados para a assinatura identificada.

    Retorna (transação_consultada, itens_verificados), em que cada item é
    (status_int, transação_decodificada, renovação_decodificada).

    O estado é fornecido pela API autenticada da Apple; os dois JWS são
    verificados criptograficamente. Somente itens que pertencem ao mesmo
    originalTransactionId da transação consultada são retornados.

    IMPORTANTE: não decide elegibilidade nem vincula a compra à conta Firebase.
    """
    tid = _validate_transaction_id(transaction_id)
    client = make_api_client(sandbox=sandbox)
    verifier = make_signed_data_verifier(sandbox=sandbox)

    transaction_response = client.get_transaction_info(tid)
    signed_initial = transaction_response.signedTransactionInfo
    if not signed_initial:
        raise ValueError("Apple não retornou transação assinada")
    initial = verifier.verify_and_decode_signed_transaction(signed_initial)
    original_id = str(getattr(initial, "originalTransactionId", "") or "")
    if not original_id:
        raise ValueError("Transação Apple sem originalTransactionId")

    response = client.get_all_subscription_statuses(original_id)
    if getattr(response, "bundleId", None) != _required_config("APPLE_BUNDLE_ID"):
        raise ValueError("Resposta Apple pertence a outro aplicativo")
    if getattr(response, "environment", None) != _environment(sandbox):
        raise ValueError("Ambiente da resposta Apple não corresponde à consulta")
    if not sandbox and getattr(response, "appAppleId", None) != int(_required_config("APPLE_APP_ID")):
        raise ValueError("App Apple ID da resposta é diferente do esperado")

    verified_items = []
    for group in (getattr(response, "data", None) or []):
        for item in (getattr(group, "lastTransactions", None) or []):
            signed_transaction = getattr(item, "signedTransactionInfo", None)
            signed_renewal = getattr(item, "signedRenewalInfo", None)
            status = getattr(item, "rawStatus", None)
            if not signed_transaction or not signed_renewal or type(status) is not int:
                raise ValueError("Resposta Apple de assinatura incompleta")
            transaction = verifier.verify_and_decode_signed_transaction(signed_transaction)
            renewal = verifier.verify_and_decode_renewal_info(signed_renewal)
            item_original = str(getattr(item, "originalTransactionId", "") or "")
            tx_original = str(getattr(transaction, "originalTransactionId", "") or "")
            renewal_original = str(getattr(renewal, "originalTransactionId", "") or "")
            if not item_original or item_original != tx_original or item_original != renewal_original:
                raise ValueError("Inconsistência nos identificadores da assinatura Apple")
            if tx_original == original_id:
                verified_items.append((status, transaction, renewal))

    if not verified_items:
        raise ValueError("Nenhum estado correspondente à assinatura consultada")
    return initial, verified_items
