from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.audit import service
from app.modules.audit.schemas import AuditPage
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.permissions.policy import Permission

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditPage)
def list_audit_events(
    action: Optional[str] = Query(default=None, max_length=80),
    status: Optional[str] = Query(default=None, pattern="^(success|failure)$"),
    actor: Optional[str] = Query(default=None, max_length=100),
    since: Optional[datetime] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
):
    items, total = service.list_events(
        db, action=action, status=status, actor=actor, since=since, limit=limit, offset=offset
    )
    return AuditPage(items=items, total=total, limit=limit, offset=offset)
