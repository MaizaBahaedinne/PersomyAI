import uuid

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.errors import Conflict, Forbidden, NotFound
from app.core.security import hash_password
from app.modules.audit import service as audit
from app.modules.authentication import service as auth_service
from app.modules.permissions.policy import Role
from app.modules.users.models import User
from app.modules.users.schemas import PasswordReset, UserCreate, UserUpdate

PRIVILEGED_ROLES = {Role.SUPER_ADMIN.value, Role.ADMIN.value}


def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise NotFound("User not found", code="user_not_found")
    return user


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def list_users(
    db: Session, *, search: str | None, role: str | None, active: bool | None, limit: int, offset: int
) -> tuple[list[User], int]:
    stmt = select(User)
    if search:
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.email).like(like), func.lower(User.display_name).like(like)))
    if role:
        stmt = stmt.where(User.role == role)
    if active is not None:
        stmt = stmt.where(User.is_active == active)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(User.created_at.asc()).limit(limit).offset(offset)).all()
    return list(rows), total


def count_active_super_admins(db: Session, exclude: uuid.UUID | None = None) -> int:
    stmt = select(func.count()).select_from(User).where(
        User.role == Role.SUPER_ADMIN.value, User.is_active.is_(True)
    )
    if exclude:
        stmt = stmt.where(User.id != exclude)
    return db.scalar(stmt) or 0


def _require_super_admin_for_privileged(actor: User, *roles: str) -> None:
    if any(r in PRIVILEGED_ROLES for r in roles) and actor.role != Role.SUPER_ADMIN.value:
        raise Forbidden(
            "Only a SUPER_ADMIN can manage administrator accounts", code="super_admin_required"
        )


def create_user(db: Session, actor: User, data: UserCreate, request: Request) -> User:
    _require_super_admin_for_privileged(actor, data.role)
    if get_by_email(db, data.email):
        raise Conflict("Email already in use", code="email_taken")
    user = User(
        email=data.email,
        display_name=data.display_name,
        password_hash=hash_password(data.password),
        role=data.role,
        preferred_language=data.preferred_language,
        is_active=True,
    )
    db.add(user)
    db.flush()
    audit.record(
        db, "user.create", request=request, actor=actor, target_type="user", target_id=user.id,
        details={"email": user.email, "role": user.role},
    )
    db.commit()
    return user


def update_user(db: Session, actor: User, target: User, data: UserUpdate, request: Request) -> User:
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return target
    is_self = actor.id == target.id
    sensitive = {"role", "is_active"} & changes.keys()
    if is_self and sensitive:
        raise Forbidden("You cannot change your own role or status", code="self_change_forbidden")

    _require_super_admin_for_privileged(actor, target.role, changes.get("role", target.role))

    new_role = changes.get("role", target.role)
    new_active = changes.get("is_active", target.is_active)
    removes_super_admin = (
        target.role == Role.SUPER_ADMIN.value
        and target.is_active
        and (new_role != Role.SUPER_ADMIN.value or not new_active)
    )
    if removes_super_admin and count_active_super_admins(db, exclude=target.id) == 0:
        raise Conflict("The last active SUPER_ADMIN cannot be removed", code="last_super_admin")

    before = {k: getattr(target, k) for k in changes}
    for key, value in changes.items():
        setattr(target, key, value)
    if "display_name" in changes:
        target.display_name = target.display_name.strip()

    revoke = ("is_active" in changes and not target.is_active) or ("role" in changes and before["role"] != target.role)
    if revoke:
        auth_service.revoke_all_sessions(db, target.id)
    action = "user.disable" if ("is_active" in changes and not target.is_active) else "user.update"
    if "is_active" in changes and target.is_active and before["is_active"] is False:
        action = "user.enable"
    audit.record(
        db, action, request=request, actor=actor, target_type="user", target_id=target.id,
        details={"changes": {k: [before[k], getattr(target, k)] for k in changes}},
    )
    target.updated_at = utcnow()
    db.commit()
    return target


def reset_password(db: Session, actor: User, target: User, data: PasswordReset, request: Request) -> None:
    if actor.role != Role.SUPER_ADMIN.value:
        raise Forbidden("Only a SUPER_ADMIN can reset passwords", code="super_admin_required")
    if actor.id == target.id:
        raise Forbidden("Use the change-password endpoint for your own account", code="self_change_forbidden")
    target.password_hash = hash_password(data.new_password)
    target.password_changed_at = utcnow()
    auth_service.revoke_all_sessions(db, target.id)
    audit.record(
        db, "user.password_reset", request=request, actor=actor, target_type="user", target_id=target.id
    )
    db.commit()
