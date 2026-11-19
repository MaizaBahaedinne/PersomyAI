import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.dashboard import service
from app.modules.permissions.policy import Permission

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class EventBrief(BaseModel):
    id: uuid.UUID
    created_at: datetime
    action: str
    actor_label: Optional[str]
    status: str


class ServiceStatus(BaseModel):
    name: str
    status: str
    latency_ms: Optional[float]


class Alert(BaseModel):
    code: str
    severity: str
    count: int


class SummaryOut(BaseModel):
    company: dict
    generated_at: datetime
    users: dict
    sessions: dict
    agents: dict
    tasks: dict
    missions: dict
    emergency_stop: bool
    security: dict
    recent_activity: list[EventBrief]
    alerts: list[Alert]
    services: list[ServiceStatus]
    pending_modules: list[str]


@router.get("/summary", response_model=SummaryOut)
def summary(
    response: Response,
    ctx: AuthContext = Depends(require_permission(Permission.DASHBOARD_READ)),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    return service.build_summary(db)
