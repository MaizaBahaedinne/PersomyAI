import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.audit import service as audit
from app.modules.authentication import service as auth_service
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.permissions.policy import Permission, Role
from app.modules.users import service
from app.modules.users.schemas import PasswordReset, UserCreate, UserOut, UserPage, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserPage)
def list_users(
    search: Optional[str] = Query(default=None, max_length=100),
    role: Optional[Role] = None,
    active: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Depends(require_permission(Permission.USERS_READ)),
    db: Session = Depends(get_db),
):
    items, total = service.list_users(
        db, search=search, role=role.value if role else None, active=active, limit=limit, offset=offset
    )
    return UserPage(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    request: Request,
    ctx: AuthContext = Depends(require_permission(Permission.USERS_WRITE)),
    db: Session = Depends(get_db),
):
    return service.create_user(db, ctx.user, payload, request)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: uuid.UUID,
    ctx: AuthContext = Depends(require_permission(Permission.USERS_READ)),
    db: Session = Depends(get_db),
):
    return service.get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    ctx: AuthContext = Depends(require_permission(Permission.USERS_WRITE)),
    db: Session = Depends(get_db),
):
    target = service.get_user(db, user_id)
    return service.update_user(db, ctx.user, target, payload, request)


@router.put("/{user_id}/password", status_code=204)
def reset_password(
    user_id: uuid.UUID,
    payload: PasswordReset,
    request: Request,
    ctx: AuthContext = Depends(require_permission(Permission.USERS_WRITE)),
    db: Session = Depends(get_db),
):
    target = service.get_user(db, user_id)
    service.reset_password(db, ctx.user, target, payload, request)
    return Response(status_code=204)


@router.delete("/{user_id}/sessions", status_code=204)
def revoke_user_sessions(
    user_id: uuid.UUID,
    request: Request,
    ctx: AuthContext = Depends(require_permission(Permission.SESSIONS_REVOKE)),
    db: Session = Depends(get_db),
):
    target = service.get_user(db, user_id)
    count = auth_service.revoke_all_sessions(db, target.id)
    audit.record(
        db, "user.sessions_revoke", request=request, actor=ctx.user, target_type="user",
        target_id=target.id, details={"revoked": count},
    )
    db.commit()
    return Response(status_code=204)
