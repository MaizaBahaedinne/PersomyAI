import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Body = Annotated[str, StringConstraints(strip_whitespace=True, max_length=8000)]
TriggerType = Literal["TASK_STATUS_CHANGED", "SCHEDULE"]
Status = Literal["DRAFT", "ACTIVE", "PAUSED"]


class AutomationCreate(BaseModel):
    name: Name
    description: Body = ""
    trigger_type: TriggerType
    trigger_config: dict = Field(default_factory=dict)
    conditions: list[dict] = Field(default_factory=list)
    actions: list[dict] = Field(default_factory=list)
    anti_loop_key: str | None = Field(default=None, min_length=1, max_length=120)
    cooldown_seconds: int = Field(default=0, ge=0, le=86400)


class AutomationUpdate(BaseModel):
    name: Name | None = None
    description: Body | None = None
    trigger_type: TriggerType | None = None
    trigger_config: dict | None = None
    conditions: list[dict] | None = None
    actions: list[dict] | None = None
    anti_loop_key: str | None = Field(default=None, min_length=1, max_length=120)
    cooldown_seconds: int | None = Field(default=None, ge=0, le=86400)


class AutomationStatusIn(BaseModel):
    status: Literal["DRAFT", "ACTIVE", "PAUSED"]
    reason: str | None = Field(default=None, max_length=500)


class TriggerSimulationIn(BaseModel):
    event_key: str = Field(min_length=1, max_length=120)


class TriggerSimulationOut(BaseModel):
    accepted: bool
    reason: str | None = None


class AutomationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    status: str
    trigger_type: str
    trigger_config: dict
    conditions: list
    actions: list
    anti_loop_key: str | None
    cooldown_seconds: int
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AutomationPage(BaseModel):
    items: list[AutomationOut]
    total: int
    limit: int
    offset: int
