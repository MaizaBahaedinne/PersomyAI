from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.permissions.policy import Permission
from app.modules.team.schemas import TeamOut
from app.modules.team.service import get_team

router = APIRouter(prefix="/team", tags=["team"])

Read = Depends(require_permission(Permission.TEAM_READ))


@router.get("", response_model=TeamOut)
def team_list(
    search: Optional[str] = Query(default=None, max_length=100),
    active: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Read,
    db: Session = Depends(get_db),
):
    return get_team(db, search=search, active=active, limit=limit, offset=offset)
