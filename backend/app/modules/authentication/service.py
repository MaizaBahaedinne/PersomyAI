import uuid
from datetime import timedelta

from fastapi import Request
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import TooManyRequests, Unauthorized
from app.core.request import client_ip, user_agent
from app.core.security import (
    fingerprint,
    generate_token,
    hash_password,
    needs_rehash,
    verify_dummy,
    verify_password,
)
from app.modules.audit import service as audit
from app.modules.authentication import two_factor
from app.modules.authentication.models import AuthSession, LoginAttempt
from app.modules.users.models import User

GENERIC_LOGIN_ERROR = "Invalid email or password"
LAST_SEEN_UPDATE_SECONDS = 60


class LoginResult:
    def __init__(self, user: User, session_token: str, csrf_token: str, session: AuthSession):
        self.user = user
        self.session_token = session_token
        self.csrf_token = csrf_token
        self.session = session


# --- Limitation des tentatives -------------------------------------------------


def _retry_after(db: Session, column, value: str, since, limit: int) -> int:
    """Secondes avant la fin du blocage (0 si pas bloqué)."""
    times = db.scalars(
        select(LoginAttempt.created_at)
        .where(column == value, LoginAttempt.success.is_(False), LoginAttempt.created_at > since)
        .order_by(LoginAttempt.created_at.desc())
    ).all()
    if len(times) < limit:
        return 0
    window = timedelta(minutes=get_settings().login_window_minutes)
    remaining = (times[limit - 1] + window - utcnow()).total_seconds()
    return max(1, int(remaining))


def check_throttle(db: Session, email: str, ip: str | None) -> int:
    s = get_settings()
    now = utcnow()
    since = now - timedelta(minutes=s.login_window_minutes)
    # Une connexion réussie remet à zéro le compteur du compte.
    last_success = db.scalar(
        select(func.max(LoginAttempt.created_at)).where(
            LoginAttempt.email == email, LoginAttempt.success.is_(True)
        )
    )
    account_since = max(since, last_success) if last_success else since
    wait = _retry_after(db, LoginAttempt.email, email, account_since, s.login_max_failures_per_account)
    if ip:
        wait = max(wait, _retry_after(db, LoginAttempt.ip_address, ip, since, s.login_max_failures_per_ip))
    return wait


def _record_attempt(db: Session, email: str, ip: str | None, success: bool) -> None:
    db.add(LoginAttempt(email=email, ip_address=ip, success=success))


def purge_old(db: Session) -> None:
    """Nettoyage opportuniste des données de session et de tentatives obsolètes."""
    now = utcnow()
    db.execute(delete(LoginAttempt).where(LoginAttempt.created_at < now - timedelta(days=30)))
    db.execute(
        delete(AuthSession).where(
            (AuthSession.expires_at < now - timedelta(days=7))
            | (AuthSession.revoked_at < now - timedelta(days=7))
        )
    )


# --- Connexion / sessions ------------------------------------------------------


def login(db: Session, request: Request, email: str, password: str, otp: str | None = None) -> LoginResult:
    s = get_settings()
    email = email.strip().lower()
    ip = client_ip(request)

    wait = check_throttle(db, email, ip)
    if wait:
        audit.record(
            db, "auth.login.blocked", request=request, actor_label=email, status="failure",
            details={"retry_after": wait},
        )
        db.commit()
        raise TooManyRequests(
            "Too many failed attempts. Try again later.",
            code="login_throttled",
            headers={"Retry-After": str(wait)},
        )

    user = db.scalar(select(User).where(User.email == email))
    reason = None
    if user is None:
        verify_dummy(password)
        reason = "unknown_user"
    elif not verify_password(user.password_hash, password):
        reason = "bad_password"
    elif not user.is_active:
        reason = "account_disabled"

    if reason:
        _record_attempt(db, email, ip, success=False)
        audit.record(
            db, "auth.login.failed", request=request, actor_label=email, status="failure",
            target_type="user", target_id=user.id if user else None, details={"reason": reason},
        )
        db.commit()
        raise Unauthorized(GENERIC_LOGIN_ERROR, code="invalid_credentials")

    assert user is not None
    second_factor = None
    if user.two_factor_enabled:
        # Le mot de passe est valide : sans code, on le demande (aucune session n'est créée, aucun échec compté).
        if not otp or not otp.strip():
            raise Unauthorized("Two-factor code required", code="two_factor_required")
        second_factor = two_factor.check_code(db, user, otp)
        if second_factor is None:
            _record_attempt(db, email, ip, success=False)
            audit.record(
                db, "auth.login.failed", request=request, actor_label=email, status="failure",
                target_type="user", target_id=user.id, details={"reason": "bad_otp"},
            )
            db.commit()
            raise Unauthorized("Invalid verification code", code="invalid_otp")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    session_token = generate_token()
    csrf_token = generate_token()
    now = utcnow()
    session = AuthSession(
        user_id=user.id,
        token_hash=fingerprint(session_token),
        csrf_hash=fingerprint(csrf_token),
        ip_address=ip,
        user_agent=user_agent(request),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=s.session_absolute_hours),
    )
    db.add(session)
    user.last_login_at = now
    _record_attempt(db, email, ip, success=True)
    db.flush()
    audit.record(
        db, "auth.login", request=request, actor=user, target_type="session", target_id=session.id,
        details={"second_factor": second_factor} if second_factor else None,
    )
    purge_old(db)
    db.commit()
    return LoginResult(user, session_token, csrf_token, session)


def resolve_session(db: Session, token: str) -> tuple[AuthSession, User] | None:
    """Retourne (session, utilisateur) si le jeton est valide, actif, non expiré."""
    s = get_settings()
    now = utcnow()
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == fingerprint(token)))
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        return None
    if session.last_seen_at + timedelta(minutes=s.session_idle_minutes) <= now:
        return None
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    if (now - session.last_seen_at).total_seconds() > LAST_SEEN_UPDATE_SECONDS:
        session.last_seen_at = now
        db.commit()
    return session, user


def revoke_session(db: Session, session: AuthSession) -> None:
    if session.revoked_at is None:
        session.revoked_at = utcnow()


def revoke_all_sessions(db: Session, user_id: uuid.UUID, except_id: uuid.UUID | None = None) -> int:
    stmt = update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    if except_id:
        stmt = stmt.where(AuthSession.id != except_id)
    return db.execute(stmt.values(revoked_at=utcnow())).rowcount or 0


def list_active_sessions(db: Session, user_id: uuid.UUID) -> list[AuthSession]:
    now = utcnow()
    return list(
        db.scalars(
            select(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
            )
            .order_by(AuthSession.created_at.desc())
        ).all()
    )


def change_password(
    db: Session, request: Request, user: User, current: AuthSession, current_password: str, new_password: str
) -> None:
    if not verify_password(user.password_hash, current_password):
        audit.record(
            db, "auth.password_change", request=request, actor=user, status="failure",
            details={"reason": "bad_current_password"},
        )
        db.commit()
        raise Unauthorized("Current password is incorrect", code="invalid_credentials")
    user.password_hash = hash_password(new_password)
    user.password_changed_at = utcnow()
    revoked = revoke_all_sessions(db, user.id, except_id=current.id)
    audit.record(
        db, "auth.password_change", request=request, actor=user, details={"other_sessions_revoked": revoked}
    )
    db.commit()
