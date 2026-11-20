from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.departments import service
from app.modules.departments.schemas import DepartmentsOut
from app.modules.permissions.policy import Permission

router = APIRouter(prefix="/departments", tags=["departments"])

Read = Depends(require_permission(Permission.DASHBOARD_READ))


@router.get("/summary", response_model=DepartmentsOut)
def departments_summary(ctx: AuthContext = Read, db: Session = Depends(get_db)):
    return DepartmentsOut(items=service.summary(db))
