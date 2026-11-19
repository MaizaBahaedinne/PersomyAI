"""Primitives de sécurité : hachage Argon2id, jetons opaques, empreintes."""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()  # Argon2id par défaut (paramètres RFC 9106 « low memory »)

# Hash factice pour égaliser le temps de réponse quand le compte n'existe pas.
_DUMMY_HASH = _hasher.hash("persomy-dummy-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_dummy(password: str) -> None:
    verify_password(_DUMMY_HASH, password)


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def generate_token() -> str:
    """Jeton opaque de 256 bits, cryptographiquement sûr."""
    return secrets.token_urlsafe(32)


def fingerprint(token: str) -> str:
    """Empreinte SHA-256 d'un jeton ; seule l'empreinte est stockée en base."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
