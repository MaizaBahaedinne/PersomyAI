from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.agents.models import Agent
from app.modules.departments.catalog import DEPARTMENTS


def summary(db: Session) -> list[dict]:
    rows = db.execute(
        select(Agent.department, Agent.status, func.count())
        .group_by(Agent.department, Agent.status)
    ).all()

    matrix = {
        code: {"agents_total": 0, "agents_active": 0, "agents_paused": 0}
        for code in DEPARTMENTS
    }
    for department, status, count in rows:
        if department not in matrix:
            continue
        matrix[department]["agents_total"] += count
        if status == "ACTIVE":
            matrix[department]["agents_active"] += count
        if status == "PAUSED":
            matrix[department]["agents_paused"] += count

    return [{"code": code, **matrix[code]} for code in DEPARTMENTS]
