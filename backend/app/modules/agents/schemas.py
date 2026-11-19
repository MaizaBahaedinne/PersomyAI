import json
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.modules.agents.catalog import AUTONOMY_LEVELS, SCOPES, SETTABLE_STATUSES, STATUSES, TOOLS
from app.modules.audit.schemas import AuditPage  # noqa: F401  (réexporté pour le routeur)
from app.modules.departments.catalog import DEPARTMENTS

MAX_CONFIG_BYTES = 8192
MAX_CONFIG_DEPTH = 6
_SECRET_WORDS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "passwd",
    "token",
    "authorization",
    "credential",
    "private_key",
)


def _scan_config(value: Any, depth: int = 0) -> None:
    if depth > MAX_CONFIG_DEPTH:
        raise ValueError("config is nested too deeply")
    if isinstance(value, dict):
        for key, item in value.items():
            if any(word in str(key).lower() for word in _SECRET_WORDS):
                raise ValueError(f"config key '{key}' looks like a secret: secrets are never stored in agent config")
            _scan_config(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _scan_config(item, depth + 1)


def _check_config(value: dict[str, Any]) -> dict[str, Any]:
    _scan_config(value)
    if len(json.dumps(value)) > MAX_CONFIG_BYTES:
        raise ValueError(f"config must not exceed {MAX_CONFIG_BYTES} bytes")
    return value


def _check_department(value: str) -> str:
    if value not in DEPARTMENTS:
        raise ValueError(f"department must be one of: {', '.join(DEPARTMENTS)}")
    return value


def _norm_skills(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in values:
        skill = raw.strip()
        if not skill:
            continue
        if len(skill) > 60:
            raise ValueError("each skill must not exceed 60 characters")
        if skill.lower() not in seen:
            seen.add(skill.lower())
            result.append(skill)
    if len(result) > 30:
        raise ValueError("at most 30 skills")
    return result


def _check_scopes(values: list[str]) -> list[str]:
    unknown = sorted(set(values) - set(SCOPES))
    if unknown:
        raise ValueError(f"unknown agent permission(s): {', '.join(unknown)}")
    return sorted(set(values))


def _check_tools(values: list[str]) -> list[str]:
    unknown = sorted(set(values) - set(TOOLS))
    if unknown:
        raise ValueError(f"unknown tool(s): {', '.join(unknown)}")
    return sorted(set(values))


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Department = Annotated[str, AfterValidator(_check_department)]
Skills = Annotated[list[str], AfterValidator(_norm_skills), Field(max_length=60)]
Config = Annotated[dict[str, Any], AfterValidator(_check_config)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Mission = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
Limit = Annotated[int, Field(ge=0, le=100_000)]
Budget = Annotated[int, Field(ge=0, le=10_000_000)]


class AgentCreate(BaseModel):
    name: Name
    description: Description = ""
    department: Department
    role: Name
    mission: Mission = ""
    skills: Skills = []
    config: Config = {}
    max_actions_per_day: Limit = 50
    monthly_budget_cents: Budget = 0


class AgentUpdate(BaseModel):
    name: Optional[Name] = None
    description: Optional[Description] = None
    department: Optional[Department] = None
    role: Optional[Name] = None
    mission: Optional[Mission] = None
    skills: Optional[Skills] = None
    config: Optional[Config] = None
    max_actions_per_day: Optional[Limit] = None
    monthly_budget_cents: Optional[Budget] = None
    autonomy_level: Optional[int] = Field(default=None, ge=min(AUTONOMY_LEVELS), le=max(AUTONOMY_LEVELS))


class StatusChange(BaseModel):
    status: Literal["DRAFT", "ACTIVE", "PAUSED", "DISABLED"]
    reason: Optional[str] = Field(default=None, max_length=500)


class ScopesUpdate(BaseModel):
    permissions: Annotated[list[str], AfterValidator(_check_scopes)]


class ToolsUpdate(BaseModel):
    tools: Annotated[list[str], AfterValidator(_check_tools)]


class AgentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identity_key: str
    name: str
    department: str
    role: str
    skills: list[str]
    status: str
    autonomy_level: int
    updated_at: datetime


class AgentOut(AgentSummary):
    description: str
    mission: str
    config: dict[str, Any]
    max_actions_per_day: int
    monthly_budget_cents: int
    access_revoked_at: Optional[datetime]
    created_at: datetime
    permissions: list[str] = []
    tools: list[str] = []


class AgentPage(BaseModel):
    items: list[AgentSummary]
    total: int
    limit: int
    offset: int


class ScopeInfo(BaseModel):
    code: str
    critical: bool


class CatalogOut(BaseModel):
    departments: list[str]
    statuses: list[str]
    settable_statuses: list[str]
    scopes: list[ScopeInfo]
    tools: list[str]
    autonomy_levels: list[int]


class EmergencyOut(BaseModel):
    active: bool
    at: Optional[str] = None
    by: Optional[str] = None
    paused_agents: int = 0


def build_catalog() -> CatalogOut:
    return CatalogOut(
        departments=list(DEPARTMENTS),
        statuses=list(STATUSES),
        settable_statuses=list(SETTABLE_STATUSES),
        scopes=[ScopeInfo(code=c, critical=crit) for c, crit in SCOPES.items()],
        tools=list(TOOLS),
        autonomy_levels=list(AUTONOMY_LEVELS),
    )
