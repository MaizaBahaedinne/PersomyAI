"""Authentification à deux facteurs (TOTP) et codes de secours."""

import secrets

from fastapi import Request
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.core import crypto, totp
from app.core.db import utcnow
from app.core.errors import Conflict, TooManyRequests, Unauthorized
from app.core.request import client_ip
from app.core.security import fingerprint, verify_password
from app.modules.audit import service as audit
from app.modules.authentication.models import AuthSession, RecoveryCode
from app.modules.users.models import User

RECOVERY_CODE_COUNT = 10
# 32 symboles sans caractères ambigus (ni l, ni o, ni 0, ni 1) : 10 caractères = 50 bits.
_ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"


def _normalize_recovery(code: str) -> str:
    return code.strip().lower().replace("-", "").replace(" ", "")


def _new_recovery_codes() -> list[str]:
    codes = []
    for _ in range(RECOVERY_CODE_COUNT):
        raw = "".join(secrets.choice(_ALPHABET) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes


def _store_recovery_codes(db: Session, user: User) -> list[str]:
    db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))
    codes = _new_recovery_codes()
    for code in codes:
        db.add(RecoveryCode(user_id=user.id, code_hash=fingerprint(_normalize_recovery(code))))
    return codes


def recovery_codes_left(db: Session, user: User) -> int:
    return db.scalar(
        select(func.count()).select_from(RecoveryCode).where(
            RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None)
        )
    ) or 0


def check_code(db: Session, user: User, code: str) -> str | None:
    """Valide un code TOTP ou de secours. Retourne "totp", "recovery" ou None.

    Chaque code n'est accepté qu'une fois (pas de temps consommé / code de secours marqué utilisé,
    de façon atomique). Le commit est laissé à l'appelant.
    """
    code = code.strip()
    if not user.two_factor_enabled or not user.two_factor_secret_encrypted:
        return None
    compact = code.replace(" ", "")
    if len(compact) == totp.DIGITS and compact.isascii() and compact.isdigit():
        secret = crypto.decrypt_secret(user.two_factor_secret_encrypted)
        step = totp.verify(secret, compact, after_step=user.two_factor_last_step)
        if step is None:
            return None
        claimed = db.execute(
            update(User)
            .where(User.id == user.id, or_(User.two_factor_last_step.is_(None), User.two_factor_last_step < step))
            .values(two_factor_last_step=step)
        ).rowcount
        if claimed != 1:
            return None
        user.two_factor_last_step = step
        return "totp"

    row = db.scalar(
        select(RecoveryCode).where(
            RecoveryCode.user_id == user.id,
            RecoveryCode.code_hash == fingerprint(_normalize_recovery(code)),
            RecoveryCode.used_at.is_(None),
        )
    )
    if row is None:
        return None
    claimed = db.execute(
        update(RecoveryCode).where(RecoveryCode.id == row.id, RecoveryCode.used_at.is_(None)).values(used_at=utcnow())
    ).rowcount
    return "recovery" if claimed == 1 else None


def _guard(db: Session, request: Request, user: User, password: str, code: str, action: str) -> str:
    """Mot de passe + code valides, sous la même limitation de tentatives que la connexion."""
    from app.modules.authentication import service as auth  # import tardif : évite une dépendance circulaire

    wait = auth.check_throttle(db, user.email, client_ip(request))
    if wait:
        raise TooManyRequests(
            "Too many failed attempts. Try again later.", code="login_throttled", headers={"Retry-After": str(wait)}
        )
    if not verify_password(user.password_hash, password):
        reason = "bad_password"
    else:
        method = check_code(db, user, code)
        if method:
            return method
        reason = "bad_code"
    auth._record_attempt(db, user.email, client_ip(request), success=False)
    audit.record(db, action, request=request, actor=user, status="failure", details={"reason": reason})
    db.commit()
    raise Unauthorized(
        "Invalid password" if reason == "bad_password" else "Invalid verification code",
        code="invalid_credentials" if reason == "bad_password" else "invalid_otp",
    )


def status(db: Session, user: User) -> dict:
    return {
        "enabled": user.two_factor_enabled,
        "available": crypto.is_available(),
        "recovery_codes_left": recovery_codes_left(db, user) if user.two_factor_enabled else 0,
    }


def begin_setup(db: Session, request: Request, user: User, password: str) -> tuple[str, str, str]:
    if user.two_factor_enabled:
        raise Conflict("Two-factor authentication is already enabled", code="two_factor_already_enabled")
    if not verify_password(user.password_hash, password):
        audit.record(
            db, "auth.2fa_setup", request=request, actor=user, status="failure", details={"reason": "bad_password"}
        )
        db.commit()
        raise Unauthorized("Invalid password", code="invalid_credentials")
    secret = totp.generate_secret()
    user.two_factor_secret_encrypted = crypto.encrypt_secret(secret)  # lève two_factor_unavailable sans clé
    user.two_factor_last_step = None
    audit.record(db, "auth.2fa_setup", request=request, actor=user)
    db.commit()
    uri = totp.provisioning_uri(secret, user.email)
    return secret, uri, totp.provisioning_qr_svg_data_uri(uri)


def enable(db: Session, request: Request, user: User, current: AuthSession, code: str) -> list[str]:
    if user.two_factor_enabled:
        raise Conflict("Two-factor authentication is already enabled", code="two_factor_already_enabled")
    if not user.two_factor_secret_encrypted:
        raise Conflict("Two-factor setup was not started", code="two_factor_not_started")
    secret = crypto.decrypt_secret(user.two_factor_secret_encrypted)
    step = totp.verify(secret, code.strip().replace(" ", ""))
    if step is None:
        audit.record(
            db, "auth.2fa_enable", request=request, actor=user, status="failure", details={"reason": "bad_code"}
        )
        db.commit()
        raise Unauthorized("Invalid verification code", code="invalid_otp")
    user.two_factor_enabled = True
    user.two_factor_last_step = step
    codes = _store_recovery_codes(db, user)
    # Les autres appareils connectés doivent désormais passer par le second facteur.
    others = db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None), AuthSession.id != current.id)
        .values(revoked_at=utcnow())
    ).rowcount or 0
    audit.record(db, "auth.2fa_enable", request=request, actor=user, details={"other_sessions_revoked": others})
    db.commit()
    return codes


def disable(db: Session, request: Request, user: User, password: str, code: str) -> None:
    if not user.two_factor_enabled:
        raise Conflict("Two-factor authentication is not enabled", code="two_factor_not_enabled")
    method = _guard(db, request, user, password, code, "auth.2fa_disable")
    _clear(db, user)
    audit.record(db, "auth.2fa_disable", request=request, actor=user, details={"method": method})
    db.commit()


def regenerate_recovery_codes(db: Session, request: Request, user: User, password: str, code: str) -> list[str]:
    if not user.two_factor_enabled:
        raise Conflict("Two-factor authentication is not enabled", code="two_factor_not_enabled")
    method = _guard(db, request, user, password, code, "auth.2fa_recovery_regenerate")
    codes = _store_recovery_codes(db, user)
    audit.record(db, "auth.2fa_recovery_regenerate", request=request, actor=user, details={"method": method})
    db.commit()
    return codes


def _clear(db: Session, user: User) -> None:
    user.two_factor_enabled = False
    user.two_factor_secret_encrypted = None
    user.two_factor_last_step = None
    db.execute(delete(RecoveryCode).where(RecoveryCode.user_id == user.id))


def reset(db: Session, user: User, actor_label: str = "cli") -> int:
    """Réinitialisation administrative (appareil perdu) : désactive la 2FA et révoque toutes les sessions."""
    _clear(db, user)
    revoked = db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    ).rowcount or 0
    audit.record(
        db, "auth.2fa_reset", actor_label=actor_label, target_type="user", target_id=user.id,
        details={"sessions_revoked": revoked},
    )
    return revoked
