import logging
import uuid
from datetime import timedelta
from typing import NoReturn

from fastapi import Request
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import utcnow
from app.core.errors import Conflict, Forbidden, NotFound
from app.modules.agents import service as agents_service
from app.modules.agents.catalog import SCOPES
from app.modules.agents.models import Agent
from app.modules.audit import service as audit
from app.modules.audit.models import AuditEvent
from app.modules.orchestration import providers
from app.modules.orchestration.catalog import (
    CANCELLABLE_STATUSES,
    LOCKED_STATUSES,
    MAX_OUTPUT_CHARS,
    MISSION_STATUSES,
    REOPENABLE_STATUSES,
    RUNNABLE_STATUSES,
    STALE_RUNNING_SECONDS,
    TASK_STATUSES,
)
from app.modules.orchestration.models import Mission, Task, TaskRun
from app.modules.orchestration.providers import ProviderError, ProviderNotConfigured
from app.modules.orchestration.schemas import (
    MissionCreate,
    MissionOut,
    MissionUpdate,
    TaskCreate,
    TaskOut,
    TaskSummary,
    TaskUpdate,
)
from app.modules.users.models import User

logger = logging.getLogger("persomy.orchestration")


# --- Règles ---------------------------------------------------------------------


def needs_approval(agent: Agent, scope: str | None) -> bool:
    """Validation humaine obligatoire si l'agent n'est pas pleinement autonome (niveau < 3) ou si la permission
    exigée est critique (envoi d'e-mail, publication). Une permission inconnue est traitée comme critique."""
    if agent.autonomy_level < 3:
        return True
    return scope is not None and SCOPES.get(scope, True)


def _is_critical(scope: str | None) -> bool:
    return scope is not None and SCOPES.get(scope, True)


# --- Missions -------------------------------------------------------------------


def get_mission(db: Session, mission_id: uuid.UUID) -> Mission:
    mission = db.get(Mission, mission_id)
    if not mission:
        raise NotFound("Mission not found", code="mission_not_found")
    return mission


def _mission_counts(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    result: dict[uuid.UUID, dict[str, int]] = {i: {s.lower(): 0 for s in TASK_STATUSES} for i in ids}
    if not ids:
        return result
    rows = db.execute(
        select(Task.mission_id, Task.status, func.count()).where(Task.mission_id.in_(ids)).group_by(
            Task.mission_id, Task.status
        )
    ).all()
    for mission_id, status, count in rows:
        result[mission_id][status.lower()] = count
    for counts in result.values():
        counts["total"] = sum(counts.values())
    return result


def mission_to_out(db: Session, mission: Mission) -> MissionOut:
    return mission_list_out(db, [mission])[0]


def mission_list_out(db: Session, missions: list[Mission]) -> list[MissionOut]:
    counts = _mission_counts(db, [m.id for m in missions])
    outs = []
    for m in missions:
        out = MissionOut.model_validate(m)
        out.task_counts = counts[m.id]
        outs.append(out)
    return outs


def list_missions(
    db: Session, *, search: str | None, status: str | None, limit: int, offset: int
) -> tuple[list[Mission], int]:
    stmt = select(Mission)
    if search:
        stmt = stmt.where(func.lower(Mission.title).like(f"%{search.strip().lower()}%"))
    if status:
        stmt = stmt.where(Mission.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Mission.created_at.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def create_mission(db: Session, actor: User, data: MissionCreate, request: Request) -> Mission:
    mission = Mission(title=data.title, description=data.description, status="OPEN", created_by=actor.id)
    db.add(mission)
    db.flush()
    audit.record(
        db, "mission.create", request=request, actor=actor, target_type="mission", target_id=mission.id,
        details={"title": mission.title},
    )
    db.commit()
    return mission


def update_mission(db: Session, actor: User, mission: Mission, data: MissionUpdate, request: Request) -> Mission:
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    changes = {k: v for k, v in changes.items() if getattr(mission, k) != v}
    if not changes:
        return mission
    before_status = mission.status
    for key, value in changes.items():
        setattr(mission, key, value)
    audit.record(
        db, "mission.update", request=request, actor=actor, target_type="mission", target_id=mission.id,
        details={
            "fields": sorted(changes),
            **({"status": [before_status, mission.status]} if "status" in changes else {}),
        },
    )
    db.commit()
    return mission


# --- Tâches : lecture -----------------------------------------------------------


def get_task(db: Session, task_id: uuid.UUID) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise NotFound("Task not found", code="task_not_found")
    return task


def _summaries(db: Session, tasks: list[Task]) -> list[TaskSummary]:
    agent_ids = {t.agent_id for t in tasks if t.agent_id}
    mission_ids = {t.mission_id for t in tasks if t.mission_id}
    agents = {a.id: a for a in db.scalars(select(Agent).where(Agent.id.in_(agent_ids))).all()} if agent_ids else {}
    missions = (
        {m.id: m.title for m in db.scalars(select(Mission).where(Mission.id.in_(mission_ids))).all()}
        if mission_ids
        else {}
    )
    out = []
    for t in tasks:
        agent = agents.get(t.agent_id) if t.agent_id else None
        out.append(
            TaskSummary(
                id=t.id, title=t.title, priority=t.priority, status=t.status,
                mission_id=t.mission_id, mission_title=missions.get(t.mission_id) if t.mission_id else None,
                agent_id=agent.id if agent else None, agent_name=agent.name if agent else None,
                required_scope=t.required_scope,
                requires_approval=needs_approval(agent, t.required_scope) if agent else None,
                created_at=t.created_at, updated_at=t.updated_at,
            )
        )
    return out


def task_summaries(db: Session, tasks: list[Task]) -> list[TaskSummary]:
    return _summaries(db, tasks)


def task_to_out(db: Session, task: Task) -> TaskOut:
    summary = _summaries(db, [task])[0]
    decided_by = db.get(User, task.decided_by) if task.decided_by else None
    return TaskOut(
        **summary.model_dump(),
        description=task.description,
        approval_requested_at=task.approval_requested_at,
        decided_by_label=decided_by.email if decided_by else None,
        decided_at=task.decided_at,
        decision_reason=task.decision_reason,
    )


def list_tasks(
    db: Session,
    *,
    search: str | None,
    status: str | None,
    agent_id: uuid.UUID | None,
    mission_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Task], int]:
    stmt = select(Task)
    if search:
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(Task.title).like(like), func.lower(Task.description).like(like)))
    if status:
        stmt = stmt.where(Task.status == status)
    if agent_id:
        stmt = stmt.where(Task.agent_id == agent_id)
    if mission_id:
        stmt = stmt.where(Task.mission_id == mission_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Task.created_at.desc()).limit(limit).offset(offset)).all()
    return list(rows), total


def runs_of(db: Session, task_id: uuid.UUID, limit: int = 20) -> list[TaskRun]:
    return list(
        db.scalars(select(TaskRun).where(TaskRun.task_id == task_id).order_by(TaskRun.started_at.desc()).limit(limit))
    )


def task_counts(db: Session) -> dict[str, int]:
    counts = {s.lower(): 0 for s in TASK_STATUSES}
    for status, count in db.execute(select(Task.status, func.count()).group_by(Task.status)).all():
        counts[status.lower()] = count
    counts["total"] = sum(counts.values())
    return counts


def mission_counts(db: Session) -> dict[str, int]:
    counts = {s.lower(): 0 for s in MISSION_STATUSES}
    for status, count in db.execute(select(Mission.status, func.count()).group_by(Mission.status)).all():
        counts[status.lower()] = count
    counts["total"] = sum(counts.values())
    return counts


# --- Tâches : écriture ----------------------------------------------------------


def _ensure_assignable(db: Session, agent_id: uuid.UUID) -> Agent:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise NotFound("Agent not found", code="agent_not_found")
    if agent.status == "DISABLED" or agent.access_revoked_at is not None:
        raise Conflict("This agent cannot receive tasks", code="agent_not_assignable")
    return agent


def _ensure_open_mission(db: Session, mission_id: uuid.UUID) -> Mission:
    mission = get_mission(db, mission_id)
    if mission.status != "OPEN":
        raise Conflict("The mission is not open", code="mission_not_open")
    return mission


def create_task(db: Session, actor: User, data: TaskCreate, request: Request) -> Task:
    if data.mission_id:
        _ensure_open_mission(db, data.mission_id)
    if data.agent_id:
        _ensure_assignable(db, data.agent_id)
    task = Task(
        title=data.title, description=data.description, priority=data.priority, status="OPEN",
        mission_id=data.mission_id, agent_id=data.agent_id, required_scope=data.required_scope,
        created_by=actor.id,
    )
    db.add(task)
    db.flush()
    audit.record(
        db, "task.create", request=request, actor=actor, target_type="task", target_id=task.id,
        details={
            "title": task.title, "mission_id": str(task.mission_id) if task.mission_id else None,
            "agent_id": str(task.agent_id) if task.agent_id else None, "required_scope": task.required_scope,
        },
    )
    db.commit()
    return task


def _reset_approval(task: Task) -> None:
    task.requested_by = None
    task.approval_requested_at = None
    task.decided_by = None
    task.decided_at = None
    task.decision_reason = None


def update_task(db: Session, actor: User, task: Task, data: TaskUpdate, request: Request) -> Task:
    if task.status in LOCKED_STATUSES:
        raise Conflict("This task can no longer be modified", code="invalid_task_state")
    fields = data.model_fields_set
    changes: dict = {}
    for key in ("title", "description", "priority"):
        value = getattr(data, key)
        if key in fields and value is not None:
            changes[key] = value
    for key in ("agent_id", "required_scope"):  # null explicite = retirer
        if key in fields:
            changes[key] = getattr(data, key)
    changes = {k: v for k, v in changes.items() if getattr(task, k) != v}
    if not changes:
        return task
    if changes.get("agent_id"):
        _ensure_assignable(db, changes["agent_id"])
    # Toute modification du contenu invalide une validation en cours ou accordée : l'humain valide ce qu'il a lu.
    reset = bool(set(changes) - {"priority"}) and task.status in {"AWAITING_APPROVAL", "APPROVED"}
    for key, value in changes.items():
        setattr(task, key, value)
    if reset:
        task.status = "OPEN"
        _reset_approval(task)
    audit.record(
        db, "task.update", request=request, actor=actor, target_type="task", target_id=task.id,
        details={"fields": sorted(changes), "approval_reset": reset},
    )
    db.commit()
    return task


def _assigned_agent(db: Session, task: Task) -> Agent:
    agent = db.get(Agent, task.agent_id) if task.agent_id else None
    if agent is None:
        raise Conflict("Assign an agent to the task first", code="agent_required")
    return agent


def request_approval(db: Session, actor: User, task: Task, request: Request) -> Task:
    if task.status != "OPEN":
        raise Conflict("Approval can only be requested for an open task", code="invalid_task_state")
    agent = _assigned_agent(db, task)
    if not needs_approval(agent, task.required_scope):
        raise Conflict("This task does not require approval", code="approval_not_required")
    task.status = "AWAITING_APPROVAL"
    task.requested_by = actor.id
    task.approval_requested_at = utcnow()
    audit.record(
        db, "task.approval_request", request=request, actor=actor, target_type="task", target_id=task.id,
        details={"required_scope": task.required_scope, "critical": _is_critical(task.required_scope)},
    )
    db.commit()
    return task


def approve(db: Session, actor: User, task: Task, comment: str | None, request: Request) -> Task:
    if task.status != "AWAITING_APPROVAL":
        raise Conflict("The task is not awaiting approval", code="invalid_task_state")
    # Principe des quatre yeux : une action critique n'est pas validée par la personne qui l'a demandée.
    if _is_critical(task.required_scope) and actor.id in {task.created_by, task.requested_by}:
        raise Forbidden("A critical task must be approved by someone else", code="self_approval_forbidden")
    task.status = "APPROVED"
    task.decided_by = actor.id
    task.decided_at = utcnow()
    task.decision_reason = comment or None
    audit.record(
        db, "task.approve", request=request, actor=actor, target_type="task", target_id=task.id,
        details={"critical": _is_critical(task.required_scope), "required_scope": task.required_scope},
    )
    db.commit()
    return task


def reject(db: Session, actor: User, task: Task, reason: str, request: Request) -> Task:
    if task.status != "AWAITING_APPROVAL":
        raise Conflict("The task is not awaiting approval", code="invalid_task_state")
    task.status = "REJECTED"
    task.decided_by = actor.id
    task.decided_at = utcnow()
    task.decision_reason = reason
    audit.record(db, "task.reject", request=request, actor=actor, target_type="task", target_id=task.id)
    db.commit()
    return task


def cancel(db: Session, actor: User, task: Task, request: Request) -> Task:
    if task.status not in CANCELLABLE_STATUSES:
        raise Conflict("This task cannot be cancelled", code="invalid_task_state")
    previous = task.status
    task.status = "CANCELLED"
    audit.record(
        db, "task.cancel", request=request, actor=actor, target_type="task", target_id=task.id,
        details={"from": previous},
    )
    db.commit()
    return task


def _is_stale(task: Task) -> bool:
    return task.status == "RUNNING" and task.updated_at < utcnow() - timedelta(seconds=STALE_RUNNING_SECONDS)


def reopen(db: Session, actor: User, task: Task, request: Request) -> Task:
    """Rouvre une tâche échouée, rejetée, ou dont l'exécution est restée bloquée. La validation est à refaire."""
    stale = _is_stale(task)
    if task.status not in REOPENABLE_STATUSES and not stale:
        raise Conflict("This task cannot be reopened", code="invalid_task_state")
    previous = task.status
    if stale:
        for run in db.scalars(select(TaskRun).where(TaskRun.task_id == task.id, TaskRun.status == "RUNNING")):
            run.status = "FAILED"
            run.error_code = "interrupted"
            run.finished_at = utcnow()
    task.status = "OPEN"
    _reset_approval(task)
    audit.record(
        db, "task.reopen", request=request, actor=actor, target_type="task", target_id=task.id,
        details={"from": previous},
    )
    db.commit()
    return task


# --- Exécution ------------------------------------------------------------------


def _blocked(db: Session, actor: User, task: Task, request: Request, code: str, message: str) -> NoReturn:
    """Refuse l'exécution : l'état de la tâche ne change pas, mais la tentative est tracée."""
    audit.record(
        db, "task.run_blocked", request=request, actor=actor, target_type="task", target_id=task.id,
        status="failure", details={"reason": code},
    )
    db.commit()
    raise Conflict(message, code=code)


def _runs_today(db: Session, agent_id: uuid.UUID) -> int:
    start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(
        select(func.count()).select_from(TaskRun).where(TaskRun.agent_id == agent_id, TaskRun.started_at >= start)
    ) or 0


def _spent_this_month(db: Session, agent_id: uuid.UUID) -> int:
    start = utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(
        select(func.coalesce(func.sum(TaskRun.cost_cents), 0)).where(
            TaskRun.agent_id == agent_id, TaskRun.started_at >= start
        )
    ) or 0


def _recent_feedback(db: Session, task_id: uuid.UUID, limit: int = 3) -> list[str]:
    rows = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.target_type == "task", AuditEvent.target_id == str(task_id), AuditEvent.action == "task.feedback")
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
    ).all()
    out: list[str] = []
    for row in rows:
        details = row.details if isinstance(row.details, dict) else {}
        text = str(details.get("feedback") or "").strip()
        if text:
            out.append(text)
    return list(reversed(out))


def _prompts(agent: Agent, task: Task, feedback: list[str] | None = None) -> tuple[str, str]:
    system = f"You are {agent.name}, {agent.role}."
    if agent.mission.strip():
        system += f" Your mission: {agent.mission.strip()}"
    # Mode execution: deliver a concrete result, not a how-to tutorial.
    system += (
        " You are an execution agent, not a coaching chatbot. "
        "Do the work and return the final deliverable directly. "
        "Do not explain how to do it, do not provide meta-commentary, and avoid step-by-step guidance unless"
        " explicitly asked in the task."
    )
    prompt = task.title if not task.description else f"{task.title}\n\n{task.description}"
    if feedback:
        feedback_block = "\n".join(f"- {item}" for item in feedback)
        prompt += (
            "\n\nUser critique to address in this revision:\n"
            f"{feedback_block}\n"
            "Return a revised final deliverable that explicitly incorporates this feedback."
        )
    return system, prompt


def run_task(db: Session, actor: User, task: Task, request: Request, feedback: str | None = None) -> TaskRun:
    if task.status not in RUNNABLE_STATUSES:
        raise Conflict("This task cannot be run in its current status", code="invalid_task_state")

    def block(code: str, message: str) -> NoReturn:
        _blocked(db, actor, task, request, code, message)

    if task.mission_id and get_mission(db, task.mission_id).status != "OPEN":
        block("mission_not_open", "The mission is not open")
    agent = db.get(Agent, task.agent_id) if task.agent_id else None
    if agent is None:
        block("agent_required", "Assign an agent to the task first")
    if agents_service.emergency_state(db)["active"]:
        block("emergency_stop_active", "Emergency stop is active")
    if agent.status != "ACTIVE" or agent.access_revoked_at is not None:
        block("agent_not_active", "The agent is not active")
    scope = task.required_scope
    if scope and scope not in agents_service.permissions_of(db, agent.id):
        block("scope_not_granted", "The agent does not hold the required permission")
    if needs_approval(agent, scope) and task.status != "APPROVED":
        block("approval_required", "Human approval is required before running this task")
    try:
        provider = providers.get_provider()
    except ProviderNotConfigured:
        block("provider_not_configured", "No AI provider is configured")
    if _runs_today(db, agent.id) >= agent.max_actions_per_day:
        block("daily_quota_exceeded", "The agent reached its daily action limit")
    if provider.paid and _spent_this_month(db, agent.id) >= agent.monthly_budget_cents:
        block("budget_exceeded", "The agent's monthly AI budget is exhausted")

    # Prise en charge atomique : deux requêtes simultanées ne peuvent pas exécuter la même tâche deux fois.
    now = utcnow()
    claimed = db.execute(
        update(Task).where(Task.id == task.id, Task.status.in_(tuple(RUNNABLE_STATUSES))).values(
            status="RUNNING", updated_at=now
        )
    ).rowcount
    if claimed != 1:
        db.rollback()
        raise Conflict("This task is already being run", code="invalid_task_state")
    run = TaskRun(
        task_id=task.id, agent_id=agent.id, status="RUNNING", provider=provider.name,
        triggered_by=actor.id, started_at=now,
    )
    db.add(run)
    db.commit()
    db.refresh(task)

    try:
        feedback_text = (feedback or "").strip()
        if feedback_text:
            audit.record(
                db,
                "task.feedback",
                request=request,
                actor=actor,
                target_type="task",
                target_id=task.id,
                details={"feedback": feedback_text[:2000]},
            )
            db.commit()

        feedback_items = _recent_feedback(db, task.id)
        system, prompt = _prompts(agent, task, feedback=feedback_items)
        completion = provider.complete(
            system=system, prompt=prompt, timeout_seconds=get_settings().ai_timeout_seconds
        )
        run.status = "SUCCESS"
        run.output = completion.text[:MAX_OUTPUT_CHARS]
        run.cost_cents = max(0, completion.cost_cents)
        run.tokens_in = max(0, completion.tokens_in)
        run.tokens_out = max(0, completion.tokens_out)
    except ProviderError as exc:
        logger.warning("provider error task=%s code=%s", task.id, exc.code)
        run.status, run.error_code = "FAILED", exc.code
    except Exception:  # sécurité: aucune erreur interne ne doit laisser la tâche bloquée en RUNNING
        logger.exception("run pipeline crashed task=%s", task.id)
        run.status, run.error_code = "FAILED", "provider_error"
    run.finished_at = utcnow()
    task.status = "DONE" if run.status == "SUCCESS" else "FAILED"
    audit.record(
        db, "task.run", request=request, actor=actor, target_type="task", target_id=task.id,
        status="success" if run.status == "SUCCESS" else "failure",
        details={"run_id": str(run.id), "provider": run.provider, "cost_cents": run.cost_cents,
                 "error_code": run.error_code},
    )
    db.commit()
    return run
