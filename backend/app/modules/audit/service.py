import uuid
from datetime import datetime
from typing import Optional

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.request import client_ip, user_agent
from app.modules.audit.models import AuditEvent
from app.modules.users.models import User

# Mots-clés interdits dans `details` : jamais de secret dans le journal.
_FORBIDDEN_KEYS = {"password", "new_password", "current_password", "token", "secret", "api_key"}


def _clean(details: Optional[dict]) -> Optional[dict]:
    if not details:
        return None
    return {k: v for k, v in details.items() if k.lower() not in _FORBIDDEN_KEYS}


def record(
    db: Session,
    action: str,
    *,
    request: Request | None = None,
    actor: User | None = None,
    actor_label: str | None = None,
    target_type: str | None = None,
    target_id: str | uuid.UUID | None = None,
    status: str = "success",
    details: Optional[dict] = None,
) -> AuditEvent:
    """Ajoute un événement d'audit à la transaction courante (le commit reste à l'appelant)."""
    event = AuditEvent(
        action=action,
        actor_user_id=actor.id if actor else None,
        actor_label=(actor.email if actor else actor_label),
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        status=status,
        ip_address=client_ip(request) if request else None,
        user_agent=user_agent(request) if request else None,
        details=_clean(details),
    )
    db.add(event)
    db.flush()
    return event


def list_events(
    db: Session,
    *,
    action: str | None = None,
    status: str | None = None,
    actor: str | None = None,
    since: datetime | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditEvent], int]:
    stmt = select(AuditEvent)
    if target_type:
        stmt = stmt.where(AuditEvent.target_type == target_type)
    if target_id:
        stmt = stmt.where(AuditEvent.target_id == target_id)
    if action:
        stmt = stmt.where(AuditEvent.action.like(f"{action}%"))
    if status:
        stmt = stmt.where(AuditEvent.status == status)
    if actor:
        stmt = stmt.where(AuditEvent.actor_label.ilike(f"%{actor}%"))
    if since:
        stmt = stmt.where(AuditEvent.created_at >= since)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)).all()
    return list(rows), total
