import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.automations import service
from app.modules.automations.schemas import (
    AutomationCreate,
    AutomationOut,
    AutomationPage,
    AutomationStatusIn,
    AutomationUpdate,
    TriggerSimulationIn,
    TriggerSimulationOut,
)
from app.modules.permissions.policy import Permission

router = APIRouter(prefix="/automations", tags=["automations"])

Read = Depends(require_permission(Permission.AUTOMATIONS_READ))
Write = Depends(require_permission(Permission.AUTOMATIONS_WRITE))


@router.get("", response_model=AutomationPage)
def list_automations(
    search: Optional[str] = Query(default=None, max_length=100),
    status: Optional[str] = Query(default=None, pattern="^(DRAFT|ACTIVE|PAUSED)$"),
    trigger_type: Optional[str] = Query(default=None, pattern="^(TASK_STATUS_CHANGED|SCHEDULE)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Read,
    db: Session = Depends(get_db),
):
    rows, total = service.list_automations(
        db, search=search, status=status, trigger_type=trigger_type, limit=limit, offset=offset
    )
    return AutomationPage(items=rows, total=total, limit=limit, offset=offset)


@router.post("", response_model=AutomationOut, status_code=201)
def create_automation(payload: AutomationCreate, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)):
    return service.create_automation(db, ctx.user, payload, request)


@router.get("/{automation_id}", response_model=AutomationOut)
def get_automation(automation_id: uuid.UUID, ctx: AuthContext = Read, db: Session = Depends(get_db)):
    return service.get_automation(db, automation_id)


@router.patch("/{automation_id}", response_model=AutomationOut)
def update_automation(
    automation_id: uuid.UUID,
    payload: AutomationUpdate,
    request: Request,
    ctx: AuthContext = Write,
    db: Session = Depends(get_db),
):
    row = service.get_automation(db, automation_id)
    return service.update_automation(db, ctx.user, row, payload, request)


@router.post("/{automation_id}/status", response_model=AutomationOut)
def change_status(
    automation_id: uuid.UUID,
    payload: AutomationStatusIn,
    request: Request,
    ctx: AuthContext = Write,
    db: Session = Depends(get_db),
):
    row = service.get_automation(db, automation_id)
    return service.change_status(db, ctx.user, row, payload.status, payload.reason, request)


@router.post("/{automation_id}/simulate-trigger", response_model=TriggerSimulationOut)
def simulate_trigger(
    automation_id: uuid.UUID,
    payload: TriggerSimulationIn,
    ctx: AuthContext = Write,
    db: Session = Depends(get_db),
):
    row = service.get_automation(db, automation_id)
    accepted, reason = service.simulate_trigger(db, row, payload.event_key)
    return TriggerSimulationOut(accepted=accepted, reason=reason)
