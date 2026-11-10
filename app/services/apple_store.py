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


def fetch_verified_transaction(transaction_id: str, *, sandbox: bool = False):
    """Consulta a Apple e verifica a assinatura da transação devolvida.

    NÃO implica assinatura ativa: a camada de negócio deve examinar
    productId, expiresDate, revocationDate e os demais campos de elegibilidade.
    """
    tid = str(transaction_id or "").strip()
    if not tid or len(tid) > 128 or not tid.isascii() or not tid.isdigit():
        raise ValueError("Identificador de transação Apple inválido")
    client = make_api_client(sandbox=sandbox)
    response = client.get_transaction_info(tid)
    signed_transaction = response.signedTransactionInfo
    if not signed_transaction:
        raise ValueError("Apple não retornou transação assinada")
    verifier = make_signed_data_verifier(sandbox=sandbox)
    return verifier.verify_and_decode_signed_transaction(signed_transaction)
