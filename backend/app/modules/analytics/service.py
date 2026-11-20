from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.modules.agents.models import Agent
from app.modules.analytics.schemas import AnalyticsSummary
from app.modules.automations.models import Automation
from app.modules.crm.models import Company, Contact
from app.modules.orchestration.models import Task, TaskRun
from app.modules.users.models import User


def _count(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


def summary(db: Session) -> AnalyticsSummary:
    since = utcnow() - timedelta(days=30)

    users_total = _count(db, select(func.count()).select_from(User))
    users_active = _count(db, select(func.count()).select_from(User).where(User.is_active.is_(True)))
    users_with_2fa = _count(
        db,
        select(func.count()).select_from(User).where(User.is_active.is_(True), User.two_factor_enabled.is_(True)),
    )

    agents_total = _count(db, select(func.count()).select_from(Agent))

    automations_total = _count(db, select(func.count()).select_from(Automation))
    automations_active = _count(
        db,
        select(func.count()).select_from(Automation).where(Automation.status == "ACTIVE"),
    )

    companies_total = _count(db, select(func.count()).select_from(Company))
    contacts_total = _count(db, select(func.count()).select_from(Contact))

    tasks_total = _count(db, select(func.count()).select_from(Task))
    tasks_open = _count(db, select(func.count()).select_from(Task).where(Task.status == "OPEN"))
    tasks_done = _count(db, select(func.count()).select_from(Task).where(Task.status == "DONE"))

    task_runs_total = _count(db, select(func.count()).select_from(TaskRun))
    task_runs_success_30d = _count(
        db,
        select(func.count()).select_from(TaskRun).where(TaskRun.status == "SUCCESS", TaskRun.started_at >= since),
    )
    ai_cost_cents_30d = _count(
        db,
        select(func.coalesce(func.sum(TaskRun.cost_cents), 0)).where(TaskRun.started_at >= since),
    )

    return AnalyticsSummary(
        users_total=users_total,
        users_active=users_active,
        users_with_2fa=users_with_2fa,
        agents_total=agents_total,
        automations_total=automations_total,
        automations_active=automations_active,
        companies_total=companies_total,
        contacts_total=contacts_total,
        tasks_total=tasks_total,
        tasks_open=tasks_open,
        tasks_done=tasks_done,
        task_runs_total=task_runs_total,
        task_runs_success_30d=task_runs_success_30d,
        ai_cost_cents_30d=ai_cost_cents_30d,
    )
