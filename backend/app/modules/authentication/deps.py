from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import Forbidden, Unauthorized
from app.core.security import constant_time_equals, fingerprint
from app.modules.authentication import service
from app.modules.authentication.models import AuthSession
from app.modules.permissions.policy import Permission, has_permission
from app.modules.users.models import User

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-csrf-token"


@dataclass
class AuthContext:
    user: User
    session: AuthSession


def get_auth_context(request: Request, db: Session = Depends(get_db)) -> AuthContext:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise Unauthorized("Authentication required", code="not_authenticated")
    resolved = service.resolve_session(db, token)
    if resolved is None:
        raise Unauthorized("Session expired or invalid", code="session_invalid")
    session, user = resolved

    if request.method not in SAFE_METHODS:
        header = request.headers.get(CSRF_HEADER, "")
        if not header or not constant_time_equals(fingerprint(header), session.csrf_hash):
            raise Forbidden("CSRF token missing or invalid", code="csrf_invalid")
    return AuthContext(user=user, session=session)


def require_permission(permission: Permission) -> Callable[..., AuthContext]:
    def dependency(ctx: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not has_permission(ctx.user.role, permission):
            raise Forbidden("Insufficient permissions", code="permission_denied")
        return ctx

    return dependency
