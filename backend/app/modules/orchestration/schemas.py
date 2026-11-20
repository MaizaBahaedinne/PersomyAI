import uuid
from datetime import datetime
from typing import Annotated, Literal, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

from app.modules.agents.catalog import SCOPES
from app.modules.audit.schemas import AuditPage  # noqa: F401  (réexporté pour le routeur)


def _check_scope(value: Optional[str]) -> Optional[str]:
    if value is not None and value not in SCOPES:
        raise ValueError(f"unknown agent permission: {value}")
    return value


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Body = Annotated[str, StringConstraints(strip_whitespace=True, max_length=8000)]
Comment = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]
Scope = Annotated[Optional[str], AfterValidator(_check_scope)]
Priority = Literal["LOW", "NORMAL", "HIGH"]


# --- Missions ------------------------------------------------------------------


class MissionCreate(BaseModel):
    title: Title
    description: Body = ""


class MissionUpdate(BaseModel):
    title: Optional[Title] = None
    description: Optional[Body] = None
    status: Optional[Literal["OPEN", "DONE", "CANCELLED"]] = None


class MissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    task_counts: dict[str, int] = {}


class MissionPage(BaseModel):
    items: list[MissionOut]
    total: int
    limit: int
    offset: int


# --- Tâches --------------------------------------------------------------------


class TaskCreate(BaseModel):
    title: Title
    description: Body = ""
    priority: Priority = "NORMAL"
    mission_id: Optional[uuid.UUID] = None
    agent_id: Optional[uuid.UUID] = None
    required_scope: Scope = None


class TaskUpdate(BaseModel):
    """`agent_id` et `required_scope` explicitement à null retirent l'affectation / l'exigence."""

    title: Optional[Title] = None
    description: Optional[Body] = None
    priority: Optional[Priority] = None
    agent_id: Optional[uuid.UUID] = None
    required_scope: Scope = None


class Decision(BaseModel):
    comment: Optional[Comment] = None


class Rejection(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class RunInput(BaseModel):
    feedback: Annotated[Optional[str], StringConstraints(strip_whitespace=True, max_length=2000)] = None


class TaskSummary(BaseModel):
    id: uuid.UUID
    title: str
    priority: str
    status: str
    mission_id: Optional[uuid.UUID]
    mission_title: Optional[str]
    agent_id: Optional[uuid.UUID]
    agent_name: Optional[str]
    required_scope: Optional[str]
    # None tant qu'aucun agent n'est affecté.
    requires_approval: Optional[bool]
    created_at: datetime
    updated_at: datetime


class TaskOut(TaskSummary):
    description: str
    approval_requested_at: Optional[datetime]
    decided_by_label: Optional[str]
    decided_at: Optional[datetime]
    decision_reason: Optional[str]


class TaskPage(BaseModel):
    items: list[TaskSummary]
    total: int
    limit: int
    offset: int


class TaskRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    provider: str
    output: str
    error_code: Optional[str]
    cost_cents: int
    tokens_in: int
    tokens_out: int
    started_at: datetime
    finished_at: Optional[datetime]


class RunResult(BaseModel):
    task: TaskOut
    run: TaskRunOut


class ProviderInfo(BaseModel):
    name: str
    configured: bool
    paid: bool
