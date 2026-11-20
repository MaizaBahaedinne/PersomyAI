from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.finance import service
from app.modules.finance.schemas import FinanceSimulationIn, FinanceSimulationOut, FinanceSummary
from app.modules.permissions.policy import Permission

router = APIRouter(prefix="/finance", tags=["finance"])

Read = Depends(require_permission(Permission.FINANCE_READ))
Simulate = Depends(require_permission(Permission.FINANCE_SIMULATE))


@router.get("/summary", response_model=FinanceSummary)
def finance_summary(ctx: AuthContext = Read, db: Session = Depends(get_db)):
    return service.summary(db)


@router.post("/simulate", response_model=FinanceSimulationOut)
def finance_simulate(payload: FinanceSimulationIn, ctx: AuthContext = Simulate):
    return service.simulate(payload)
