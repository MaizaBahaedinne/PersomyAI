import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import NotFound
from app.modules.audit import service as audit
from app.modules.authentication import service, two_factor
from app.modules.authentication.deps import AuthContext, get_auth_context
from app.modules.authentication.schemas import (
    LoginRequest,
    MeOut,
    PasswordChange,
    PreferencesUpdate,
    RecoveryCodesOut,
    SessionOut,
    TwoFactorCodeIn,
    TwoFactorConfirmIn,
    TwoFactorSetupIn,
    TwoFactorSetupOut,
    TwoFactorStatus,
)
from app.modules.permissions.policy import permissions_for
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["authentication"])


def _me(user) -> MeOut:
    return MeOut(
        user=UserOut.model_validate(user),
        permissions=sorted(p.value for p in permissions_for(user.role)),
    )


def _set_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    s = get_settings()
    max_age = s.session_absolute_hours * 3600
    common = dict(max_age=max_age, path="/", secure=s.cookie_secure, samesite=s.cookie_samesite)
    response.set_cookie(s.session_cookie_name, session_token, httponly=True, **common)
    # Cookie CSRF lisible par le frontend (double envoi via l'en-tête X-CSRF-Token).
    response.set_cookie(s.csrf_cookie_name, csrf_token, httponly=False, **common)


def _clear_cookies(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(s.session_cookie_name, path="/")
    response.delete_cookie(s.csrf_cookie_name, path="/")


@router.post("/login", response_model=MeOut)
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    result = service.login(db, request, payload.email, payload.password, payload.otp)
    _set_cookies(response, result.session_token, result.csrf_token)
    response.headers["Cache-Control"] = "no-store"
    return _me(result.user)


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    service.revoke_session(db, ctx.session)
    audit.record(db, "auth.logout", request=request, actor=ctx.user, target_type="session", target_id=ctx.session.id)
    db.commit()
    result = Response(status_code=204)
    _clear_cookies(result)
    return result


@router.get("/me", response_model=MeOut)
def me(response: Response, ctx: AuthContext = Depends(get_auth_context)):
    response.headers["Cache-Control"] = "no-store"
    return _me(ctx.user)


@router.patch("/me", response_model=MeOut)
def update_me(
    payload: PreferencesUpdate,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    for key, value in changes.items():
        setattr(ctx.user, key, value.strip() if isinstance(value, str) else value)
    if changes:
        audit.record(
            db, "user.preferences_update", request=request, actor=ctx.user, details={"fields": sorted(changes)}
        )
        db.commit()
    return _me(ctx.user)


@router.post("/change-password", status_code=204)
def change_password(
    payload: PasswordChange,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    service.change_password(db, request, ctx.user, ctx.session, payload.current_password, payload.new_password)
    return Response(status_code=204)


@router.get("/2fa", response_model=TwoFactorStatus)
def two_factor_status(response: Response, ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return two_factor.status(db, ctx.user)


@router.post("/2fa/setup", response_model=TwoFactorSetupOut)
def two_factor_setup(
    payload: TwoFactorSetupIn,
    request: Request,
    response: Response,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    secret, uri = two_factor.begin_setup(db, request, ctx.user, payload.password)
    response.headers["Cache-Control"] = "no-store"
    return TwoFactorSetupOut(secret=secret, otpauth_uri=uri)


@router.post("/2fa/enable", response_model=RecoveryCodesOut)
def two_factor_enable(
    payload: TwoFactorCodeIn,
    request: Request,
    response: Response,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    codes = two_factor.enable(db, request, ctx.user, ctx.session, payload.code)
    response.headers["Cache-Control"] = "no-store"
    return RecoveryCodesOut(recovery_codes=codes)


@router.post("/2fa/disable", status_code=204)
def two_factor_disable(
    payload: TwoFactorConfirmIn,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    two_factor.disable(db, request, ctx.user, payload.password, payload.code)
    return Response(status_code=204)


@router.post("/2fa/recovery-codes", response_model=RecoveryCodesOut)
def two_factor_recovery_codes(
    payload: TwoFactorConfirmIn,
    request: Request,
    response: Response,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    codes = two_factor.regenerate_recovery_codes(db, request, ctx.user, payload.password, payload.code)
    response.headers["Cache-Control"] = "no-store"
    return RecoveryCodesOut(recovery_codes=codes)


@router.get("/sessions", response_model=list[SessionOut])
def my_sessions(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    sessions = service.list_active_sessions(db, ctx.user.id)
    return [
        SessionOut(
            id=s.id, ip_address=s.ip_address, user_agent=s.user_agent, created_at=s.created_at,
            last_seen_at=s.last_seen_at, expires_at=s.expires_at, current=(s.id == ctx.session.id),
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=204)
def revoke_my_session(
    session_id: uuid.UUID,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    target = next((s for s in service.list_active_sessions(db, ctx.user.id) if s.id == session_id), None)
    if target is None:
        raise NotFound("Session not found", code="session_not_found")
    service.revoke_session(db, target)
    audit.record(db, "auth.session_revoke", request=request, actor=ctx.user, target_type="session", target_id=target.id)
    db.commit()
    return Response(status_code=204)
