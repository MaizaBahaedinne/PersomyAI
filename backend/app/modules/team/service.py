from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.team.schemas import TeamMember, TeamOut, TeamSummary
from app.modules.users.models import User


def get_team(db: Session, *, search: str | None, active: bool | None, limit: int, offset: int) -> TeamOut:
    stmt = select(User)
    if search:
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(User.display_name).like(like) | func.lower(User.email).like(like)
        )
    if active is not None:
        stmt = stmt.where(User.is_active.is_(active))

    rows = db.scalars(stmt.order_by(func.lower(User.display_name)).limit(limit).offset(offset)).all()

    total = db.scalar(select(func.count()).select_from(User)) or 0
    active_count = db.scalar(select(func.count()).select_from(User).where(User.is_active.is_(True))) or 0
    super_admins = (
        db.scalar(
            select(func.count()).select_from(User).where(User.role == "SUPER_ADMIN", User.is_active.is_(True))
        )
        or 0
    )
    with_2fa = (
        db.scalar(select(func.count()).select_from(User).where(User.two_factor_enabled.is_(True), User.is_active.is_(True)))
        or 0
    )

    items = [
        TeamMember(
            id=str(u.id),
            display_name=u.display_name,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            preferred_language=u.preferred_language,
            two_factor_enabled=u.two_factor_enabled,
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
        )
        for u in rows
    ]

    return TeamOut(
        summary=TeamSummary(
            total=int(total),
            active=int(active_count),
            disabled=int(total - active_count),
            super_admins=int(super_admins),
            with_two_factor=int(with_2fa),
        ),
        items=items,
    )
