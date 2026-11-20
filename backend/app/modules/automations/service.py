from datetime import timedelta
import uuid

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.errors import Conflict, NotFound
from app.modules.audit import service as audit
from app.modules.automations.models import Automation
from app.modules.automations.schemas import AutomationCreate, AutomationUpdate
from app.modules.users.models import User


def get_automation(db: Session, automation_id: uuid.UUID) -> Automation:
    row = db.get(Automation, automation_id)
    if not row:
        raise NotFound("Automation not found", code="automation_not_found")
    return row


def _validate(actions: list[dict], trigger_type: str) -> None:
    if len(actions) == 0:
        raise Conflict("Automation needs at least one action", code="automation_action_required")
    # Empêche la boucle directe : une automation déclenchée par statut de tâche
    # ne peut pas immédiatement rejouer le même événement.
    if trigger_type == "TASK_STATUS_CHANGED":
        for action in actions:
            if action.get("type") == "task.set_status":
                raise Conflict("Action can loop with this trigger", code="automation_loop_risk")


def create_automation(db: Session, actor: User, payload: AutomationCreate, request: Request) -> Automation:
    _validate(payload.actions, payload.trigger_type)
    exists = db.scalar(select(Automation.id).where(func.lower(Automation.name) == payload.name.lower()))
    if exists:
        raise Conflict("Automation name already exists", code="automation_name_taken")
    row = Automation(**payload.model_dump(), created_by=actor.id)
    db.add(row)
    db.flush()
    audit.record(
        db,
        "automation.create",
        request=request,
        actor=actor,
        target_type="automation",
        target_id=row.id,
        details={"name": row.name, "trigger_type": row.trigger_type, "status": row.status},
    )
    db.commit()
    return row


def update_automation(db: Session, actor: User, row: Automation, payload: AutomationUpdate, request: Request) -> Automation:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return row
    if "name" in changes:
        exists = db.scalar(
            select(Automation.id).where(func.lower(Automation.name) == changes["name"].lower(), Automation.id != row.id)
        )
        if exists:
            raise Conflict("Automation name already exists", code="automation_name_taken")
    actions = changes.get("actions", row.actions)
    trigger_type = changes.get("trigger_type", row.trigger_type)
    _validate(actions, trigger_type)

    for key, value in changes.items():
        setattr(row, key, value)

    audit.record(
        db,
        "automation.update",
        request=request,
        actor=actor,
        target_type="automation",
        target_id=row.id,
        details={"fields": sorted(changes.keys())},
    )
    db.commit()
    return row


def change_status(
    db: Session, actor: User, row: Automation, status: str, reason: str | None, request: Request
) -> Automation:
    if row.status == status:
        raise Conflict("Status unchanged", code="automation_status_unchanged")
    if status == "ACTIVE":
        _validate(row.actions, row.trigger_type)
    old = row.status
    row.status = status
    audit.record(
        db,
        "automation.status",
        request=request,
        actor=actor,
        target_type="automation",
        target_id=row.id,
        details={"from": old, "to": status, "reason": reason},
    )
    db.commit()
    return row


def list_automations(
    db: Session, *, search: str | None, status: str | None, trigger_type: str | None, limit: int, offset: int
) -> tuple[list[Automation], int]:
    stmt = select(Automation)
    if search:
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(Automation.name).like(like), func.lower(Automation.description).like(like)))
    if status:
        stmt = stmt.where(Automation.status == status)
    if trigger_type:
        stmt = stmt.where(Automation.trigger_type == trigger_type)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(func.lower(Automation.name)).limit(limit).offset(offset)).all()
    return list(rows), total


def simulate_trigger(db: Session, row: Automation, event_key: str) -> tuple[bool, str | None]:
    if row.status != "ACTIVE":
        return False, "automation_not_active"
    now = utcnow()
    if row.anti_loop_key and row.anti_loop_key == event_key and row.last_triggered_at and row.cooldown_seconds > 0:
        if now - row.last_triggered_at < timedelta(seconds=row.cooldown_seconds):
            return False, "automation_loop_blocked"
    row.last_triggered_at = now
    db.commit()
    return True, None
