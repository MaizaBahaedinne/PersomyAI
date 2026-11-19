"""Chiffrement des secrets applicatifs au repos (Fernet : AES-128-CBC + HMAC-SHA256).

La clé vient de `TWO_FACTOR_KEY` (jamais en base). Sans clé valide, la 2FA est indisponible : aucun secret
n'est écrit en clair.
"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.errors import Conflict


class TwoFactorUnavailable(Conflict):
    code = "two_factor_unavailable"


def _fernet() -> Fernet:
    key = get_settings().two_factor_key.strip()
    if not key:
        raise TwoFactorUnavailable("Two-factor encryption key is not configured")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError):
        raise TwoFactorUnavailable("Two-factor encryption key is invalid") from None


def is_available() -> bool:
    try:
        _fernet()
    except TwoFactorUnavailable:
        return False
    return True


def encrypt_secret(plain: str) -> str:
    return _fernet().encrypt(plain.encode("ascii")).decode("ascii")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("ascii")
    except InvalidToken:
        raise TwoFactorUnavailable("Stored two-factor secret cannot be decrypted with the current key") from None
