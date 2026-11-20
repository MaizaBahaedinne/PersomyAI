from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.analytics.schemas import AnalyticsSummary
from app.modules.analytics.service import summary
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.permissions.policy import Permission

router = APIRouter(prefix="/analytics", tags=["analytics"])

Read = Depends(require_permission(Permission.ANALYTICS_READ))


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(ctx: AuthContext = Read, db: Session = Depends(get_db)):
    return summary(db)
