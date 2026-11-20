"""TOTP (RFC 6238) : SHA-1, 6 chiffres, pas de 30 s. Implémentation standard sans dépendance externe."""

import base64
import hashlib
import hmac
from io import BytesIO
import secrets
import struct
import time
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6
ISSUER = "Persomy AI"


def generate_secret() -> str:
    """Secret de 160 bits encodé en base32 (32 caractères, sans remplissage)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def _hotp(secret: str, counter: int) -> str:
    key = base64.b32decode(secret + "=" * (-len(secret) % 8), casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 10**DIGITS:0{DIGITS}d}"


def current_step(now: float | None = None) -> int:
    return int((time.time() if now is None else now) // STEP_SECONDS)


def verify(
    secret: str, code: str, *, now: float | None = None, window: int = 1, after_step: int | None = None
) -> int | None:
    """Retourne le pas de temps correspondant au code, ou None.

    `window` tolère un décalage d'horloge de ±window pas. `after_step` refuse tout pas déjà consommé
    (protection contre le rejeu d'un code déjà accepté).
    """
    if len(code) != DIGITS or not code.isascii() or not code.isdigit():
        return None
    step = current_step(now)
    matched: int | None = None
    for candidate in range(step - window, step + window + 1):
        if after_step is not None and candidate <= after_step:
            continue
        if hmac.compare_digest(_hotp(secret, candidate), code):
            matched = candidate
    return matched


def provisioning_uri(secret: str, account: str) -> str:
    label = quote(f"{ISSUER}:{account}", safe="")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(ISSUER, safe='')}"
        f"&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"
    )


def provisioning_qr_svg_data_uri(uri: str) -> str:
    """Génère un QR SVG inline (data URI) pour éviter tout appel externe."""
    import qrcode  # type: ignore[import-not-found]
    from qrcode.image.svg import SvgPathImage  # type: ignore[import-not-found]

    img = qrcode.make(uri, image_factory=SvgPathImage, box_size=6, border=2)
    buff = BytesIO()
    img.save(buff)
    data = base64.b64encode(buff.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{data}"
