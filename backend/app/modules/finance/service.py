from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.modules.finance.schemas import FinanceSimulationIn, FinanceSimulationOut, FinanceSummary
from app.modules.orchestration.models import TaskRun


def summary(db: Session) -> FinanceSummary:
    now = utcnow()
    since_30d = now - timedelta(days=30)

    total_runs = db.scalar(select(func.count()).select_from(TaskRun)) or 0
    total_cost = db.scalar(select(func.coalesce(func.sum(TaskRun.cost_cents), 0))) or 0
    cost_30d = (
        db.scalar(
            select(func.coalesce(func.sum(TaskRun.cost_cents), 0)).where(TaskRun.started_at >= since_30d)
        )
        or 0
    )
    avg = float(total_cost / total_runs) if total_runs else 0.0

    return FinanceSummary(
        task_runs_total=int(total_runs),
        cost_cents_total=int(total_cost),
        cost_cents_30d=int(cost_30d),
        average_cost_cents=round(avg, 2),
    )


def simulate(payload: FinanceSimulationIn) -> FinanceSimulationOut:
    projected_revenue = int(payload.monthly_revenue_cents * (1 + payload.growth_percent / 100))
    projected_margin = int(projected_revenue * (payload.gross_margin_percent / 100))
    margin_after_ai = projected_margin - payload.ai_cost_cents_monthly
    ai_share = (payload.ai_cost_cents_monthly / projected_revenue * 100) if projected_revenue else 0.0

    return FinanceSimulationOut(
        projected_revenue_cents=projected_revenue,
        projected_margin_cents=projected_margin,
        margin_after_ai_cents=margin_after_ai,
        ai_cost_share_percent=round(ai_share, 2),
    )
