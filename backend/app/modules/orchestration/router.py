import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.audit import service as audit
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.orchestration import providers, service
from app.modules.orchestration.schemas import (
    AuditPage,
    Decision,
    MissionCreate,
    MissionOut,
    MissionPage,
    MissionUpdate,
    ProviderInfo,
    Rejection,
    RunInput,
    RunResult,
    TaskCreate,
    TaskOut,
    TaskPage,
    TaskRunOut,
    TaskUpdate,
)
from app.modules.permissions.policy import Permission

missions_router = APIRouter(prefix="/missions", tags=["missions"])
tasks_router = APIRouter(prefix="/tasks", tags=["tasks"])

Read = Depends(require_permission(Permission.ORCHESTRATION_READ))
Write = Depends(require_permission(Permission.ORCHESTRATION_WRITE))
Approve = Depends(require_permission(Permission.ORCHESTRATION_APPROVE))
Run = Depends(require_permission(Permission.ORCHESTRATION_RUN))

_TASK_STATUS = "^(OPEN|AWAITING_APPROVAL|APPROVED|RUNNING|DONE|FAILED|REJECTED|CANCELLED)$"


# --- Missions ------------------------------------------------------------------


@missions_router.get("", response_model=MissionPage)
def list_missions(
    search: Optional[str] = Query(default=None, max_length=100),
    status: Optional[str] = Query(default=None, pattern="^(OPEN|DONE|CANCELLED)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Read,
    db: Session = Depends(get_db),
):
    rows, total = service.list_missions(db, search=search, status=status, limit=limit, offset=offset)
    return MissionPage(items=service.mission_list_out(db, rows), total=total, limit=limit, offset=offset)


@missions_router.post("", response_model=MissionOut, status_code=201)
def create_mission(payload: MissionCreate, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)):
    return service.mission_to_out(db, service.create_mission(db, ctx.user, payload, request))


@missions_router.get("/{mission_id}", response_model=MissionOut)
def get_mission(mission_id: uuid.UUID, ctx: AuthContext = Read, db: Session = Depends(get_db)):
    return service.mission_to_out(db, service.get_mission(db, mission_id))


@missions_router.patch("/{mission_id}", response_model=MissionOut)
def update_mission(
    mission_id: uuid.UUID,
    payload: MissionUpdate,
    request: Request,
    ctx: AuthContext = Write,
    db: Session = Depends(get_db),
):
    mission = service.get_mission(db, mission_id)
    return service.mission_to_out(db, service.update_mission(db, ctx.user, mission, payload, request))


# --- Tâches --------------------------------------------------------------------


# Route statique déclarée avant /{task_id}.
@tasks_router.get("/provider", response_model=ProviderInfo)
def provider_info(ctx: AuthContext = Read):
    return ProviderInfo(**providers.provider_info())


@tasks_router.get("", response_model=TaskPage)
def list_tasks(
    search: Optional[str] = Query(default=None, max_length=100),
    status: Optional[str] = Query(default=None, pattern=_TASK_STATUS),
    agent_id: Optional[uuid.UUID] = None,
    mission_id: Optional[uuid.UUID] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Read,
    db: Session = Depends(get_db),
):
    rows, total = service.list_tasks(
        db, search=search, status=status, agent_id=agent_id, mission_id=mission_id, limit=limit, offset=offset
    )
    return TaskPage(items=service.task_summaries(db, rows), total=total, limit=limit, offset=offset)


@tasks_router.post("", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)):
    return service.task_to_out(db, service.create_task(db, ctx.user, payload, request))


@tasks_router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: uuid.UUID, ctx: AuthContext = Read, db: Session = Depends(get_db)):
    return service.task_to_out(db, service.get_task(db, task_id))


@tasks_router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: uuid.UUID, payload: TaskUpdate, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)
):
    task = service.get_task(db, task_id)
    return service.task_to_out(db, service.update_task(db, ctx.user, task, payload, request))


@tasks_router.post("/{task_id}/request-approval", response_model=TaskOut)
def request_approval(task_id: uuid.UUID, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)):
    task = service.get_task(db, task_id)
    return service.task_to_out(db, service.request_approval(db, ctx.user, task, request))


@tasks_router.post("/{task_id}/approve", response_model=TaskOut)
def approve_task(
    task_id: uuid.UUID,
    request: Request,
    payload: Decision = Decision(),
    ctx: AuthContext = Approve,
    db: Session = Depends(get_db),
):
    task = service.get_task(db, task_id)
    return service.task_to_out(db, service.approve(db, ctx.user, task, payload.comment, request))


@tasks_router.post("/{task_id}/reject", response_model=TaskOut)
def reject_task(
    task_id: uuid.UUID, payload: Rejection, request: Request, ctx: AuthContext = Approve, db: Session = Depends(get_db)
):
    task = service.get_task(db, task_id)
    return service.task_to_out(db, service.reject(db, ctx.user, task, payload.reason, request))


@tasks_router.post("/{task_id}/cancel", response_model=TaskOut)
def cancel_task(task_id: uuid.UUID, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)):
    task = service.get_task(db, task_id)
    return service.task_to_out(db, service.cancel(db, ctx.user, task, request))


@tasks_router.post("/{task_id}/reopen", response_model=TaskOut)
def reopen_task(task_id: uuid.UUID, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)):
    task = service.get_task(db, task_id)
    return service.task_to_out(db, service.reopen(db, ctx.user, task, request))


@tasks_router.post("/{task_id}/run", response_model=RunResult)
def run_task(
    task_id: uuid.UUID,
    request: Request,
    payload: RunInput | None = None,
    ctx: AuthContext = Run,
    db: Session = Depends(get_db),
):
    task = service.get_task(db, task_id)
    run = service.run_task(db, ctx.user, task, request, feedback=(payload.feedback if payload else None))
    return RunResult(task=service.task_to_out(db, task), run=TaskRunOut.model_validate(run))


@tasks_router.get("/{task_id}/runs", response_model=list[TaskRunOut])
def task_runs(task_id: uuid.UUID, ctx: AuthContext = Read, db: Session = Depends(get_db)):
    service.get_task(db, task_id)
    return service.runs_of(db, task_id)


@tasks_router.get("/{task_id}/history", response_model=AuditPage)
def task_history(
    task_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Read,
    db: Session = Depends(get_db),
):
    service.get_task(db, task_id)
    rows, total = audit.list_events(db, target_type="task", target_id=str(task_id), limit=limit, offset=offset)
    return AuditPage(items=rows, total=total, limit=limit, offset=offset)
