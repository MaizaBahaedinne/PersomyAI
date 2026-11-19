import secrets
import uuid

from fastapi import Request
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.core.errors import Conflict, Forbidden, NotFound
from app.modules.agents.catalog import DELETABLE_STATUSES, STATUSES, TRANSITIONS
from app.modules.agents.models import Agent, AgentPermission, AgentTool
from app.modules.agents.schemas import AgentCreate, AgentOut, AgentUpdate
from app.modules.audit import service as audit
from app.modules.permissions.policy import Role
from app.modules.settings.models import SystemSetting
from app.modules.users.models import User

EMERGENCY_KEY = "emergency_stop"
# Champs courts dont on journalise l'ancienne et la nouvelle valeur.
_SMALL_FIELDS = {"name", "department", "role", "autonomy_level", "max_actions_per_day", "monthly_budget_cents"}


def _is_super_admin(actor: User) -> bool:
    return actor.role == Role.SUPER_ADMIN.value


def get_agent(db: Session, agent_id: uuid.UUID) -> Agent:
    agent = db.get(Agent, agent_id)
    if not agent:
        raise NotFound("Agent not found", code="agent_not_found")
    return agent


def permissions_of(db: Session, agent_id: uuid.UUID) -> list[str]:
    return sorted(db.scalars(select(AgentPermission.permission).where(AgentPermission.agent_id == agent_id)).all())


def tools_of(db: Session, agent_id: uuid.UUID) -> list[str]:
    return sorted(db.scalars(select(AgentTool.tool).where(AgentTool.agent_id == agent_id)).all())


def to_out(db: Session, agent: Agent) -> AgentOut:
    out = AgentOut.model_validate(agent)
    out.permissions = permissions_of(db, agent.id)
    out.tools = tools_of(db, agent.id)
    return out


def list_agents(
    db: Session, *, search: str | None, status: str | None, department: str | None, limit: int, offset: int
) -> tuple[list[Agent], int]:
    stmt = select(Agent)
    if search:
        like = f"%{search.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(Agent.name).like(like), func.lower(Agent.role).like(like)))
    if status:
        stmt = stmt.where(Agent.status == status)
    if department:
        stmt = stmt.where(Agent.department == department)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(func.lower(Agent.name)).limit(limit).offset(offset)).all()
    return list(rows), total


def status_counts(db: Session) -> dict[str, int]:
    counts = {s.lower(): 0 for s in STATUSES}
    for status, count in db.execute(select(Agent.status, func.count()).group_by(Agent.status)).all():
        counts[status.lower()] = count
    counts["total"] = sum(counts.values())
    return counts


def _ensure_name_free(db: Session, name: str, exclude: uuid.UUID | None = None) -> None:
    stmt = select(Agent.id).where(func.lower(Agent.name) == name.lower())
    if exclude:
        stmt = stmt.where(Agent.id != exclude)
    if db.scalar(stmt):
        raise Conflict("An agent with this name already exists", code="agent_name_taken")


def _require_super_admin(actor: User) -> None:
    if not _is_super_admin(actor):
        raise Forbidden("Only a SUPER_ADMIN can do this", code="super_admin_required")


# --- Cycle de vie --------------------------------------------------------------


def create_agent(db: Session, actor: User, data: AgentCreate, request: Request) -> Agent:
    _ensure_name_free(db, data.name)
    if data.monthly_budget_cents > 0:
        _require_super_admin(actor)  # aucun budget d'IA payante sans validation d'un SUPER_ADMIN
    agent = Agent(
        identity_key=f"agt_{secrets.token_hex(8)}",
        name=data.name,
        description=data.description,
        department=data.department,
        role=data.role,
        mission=data.mission,
        skills=data.skills,
        config=data.config,
        max_actions_per_day=data.max_actions_per_day,
        monthly_budget_cents=data.monthly_budget_cents,
        status="DRAFT",
        autonomy_level=1,
        created_by=actor.id,
    )
    db.add(agent)
    db.flush()
    audit.record(
        db, "agent.create", request=request, actor=actor, target_type="agent", target_id=agent.id,
        details={"name": agent.name, "department": agent.department, "identity_key": agent.identity_key},
    )
    db.commit()
    return agent


def update_agent(db: Session, actor: User, agent: Agent, data: AgentUpdate, request: Request) -> Agent:
    changes = {k: v for k, v in data.model_dump(exclude_unset=True).items() if v is not None}
    if not changes:
        return agent
    if "name" in changes:
        _ensure_name_free(db, changes["name"], exclude=agent.id)
    # Monter l'autonomie ou le budget exige un SUPER_ADMIN ; les baisser est toujours permis.
    if changes.get("autonomy_level", agent.autonomy_level) > agent.autonomy_level:
        _require_super_admin(actor)
    if changes.get("monthly_budget_cents", agent.monthly_budget_cents) > agent.monthly_budget_cents:
        _require_super_admin(actor)

    before = {k: getattr(agent, k) for k in changes}
    for key, value in changes.items():
        setattr(agent, key, value)
    audit.record(
        db, "agent.update", request=request, actor=actor, target_type="agent", target_id=agent.id,
        details={
            "fields": sorted(changes),
            "changes": {k: [before[k], changes[k]] for k in changes if k in _SMALL_FIELDS},
        },
    )
    db.commit()
    return agent


def emergency_state(db: Session) -> dict:
    row = db.get(SystemSetting, EMERGENCY_KEY)
    value = row.value if row and isinstance(row.value, dict) else {}
    return {"active": bool(value.get("active")), "at": value.get("at"), "by": value.get("by")}


def _check_can_run(db: Session, agent: Agent) -> None:
    if emergency_state(db)["active"]:
        raise Conflict("Emergency stop is active", code="emergency_stop_active")
    if not agent.mission.strip() or not agent.role.strip():
        raise Conflict("Agent needs a role and a mission before activation", code="agent_incomplete")
    if agent.access_revoked_at is not None:
        raise Conflict("Agent access is revoked", code="access_revoked")


def change_status(
    db: Session, actor: User, agent: Agent, target: str, reason: str | None, request: Request
) -> Agent:
    current = agent.status
    if current == target:
        raise Conflict("Agent already has this status", code="status_unchanged")
    if (current, target) not in TRANSITIONS:
        raise Conflict(f"Transition {current} -> {target} is not allowed", code="invalid_transition")
    if target == "ACTIVE":
        _check_can_run(db, agent)
    if target == "DRAFT":
        agent.access_revoked_at = None  # repartir d'un brouillon : permissions à ré-accorder
    agent.status = target
    audit.record(
        db, "agent.status", request=request, actor=actor, target_type="agent", target_id=agent.id,
        details={"from": current, "to": target, "reason": reason},
    )
    db.commit()
    return agent


def set_permissions(db: Session, actor: User, agent: Agent, scopes: list[str], request: Request) -> list[str]:
    if agent.access_revoked_at is not None:
        raise Conflict("Agent access is revoked: reset the agent to DRAFT first", code="access_revoked")
    current = set(permissions_of(db, agent.id))
    wanted = set(scopes)
    db.execute(
        delete(AgentPermission).where(
            AgentPermission.agent_id == agent.id, AgentPermission.permission.in_(current - wanted)
        )
    )
    for scope in sorted(wanted - current):
        db.add(AgentPermission(agent_id=agent.id, permission=scope, granted_by=actor.id))
    audit.record(
        db, "agent.permissions_update", request=request, actor=actor, target_type="agent", target_id=agent.id,
        details={"added": sorted(wanted - current), "removed": sorted(current - wanted)},
    )
    db.commit()
    return sorted(wanted)


def set_tools(db: Session, actor: User, agent: Agent, tools: list[str], request: Request) -> list[str]:
    if agent.access_revoked_at is not None:
        raise Conflict("Agent access is revoked: reset the agent to DRAFT first", code="access_revoked")
    current = set(tools_of(db, agent.id))
    wanted = set(tools)
    db.execute(delete(AgentTool).where(AgentTool.agent_id == agent.id, AgentTool.tool.in_(current - wanted)))
    for tool in sorted(wanted - current):
        db.add(AgentTool(agent_id=agent.id, tool=tool, granted_by=actor.id))
    audit.record(
        db, "agent.tools_update", request=request, actor=actor, target_type="agent", target_id=agent.id,
        details={"added": sorted(wanted - current), "removed": sorted(current - wanted)},
    )
    db.commit()
    return sorted(wanted)


def revoke_access(db: Session, actor: User, agent: Agent, request: Request) -> Agent:
    """Retire toutes les permissions et tous les outils, puis désactive l'agent."""
    removed_perms = permissions_of(db, agent.id)
    removed_tools = tools_of(db, agent.id)
    db.execute(delete(AgentPermission).where(AgentPermission.agent_id == agent.id))
    db.execute(delete(AgentTool).where(AgentTool.agent_id == agent.id))
    previous = agent.status
    agent.status = "DISABLED"
    agent.access_revoked_at = utcnow()
    audit.record(
        db, "agent.access_revoke", request=request, actor=actor, target_type="agent", target_id=agent.id,
        details={"previous_status": previous, "permissions_removed": removed_perms, "tools_removed": removed_tools},
    )
    db.commit()
    return agent


def delete_agent(db: Session, actor: User, agent: Agent, request: Request) -> None:
    if agent.status not in DELETABLE_STATUSES:
        raise Conflict("Only DRAFT or DISABLED agents can be deleted", code="agent_not_deletable")
    snapshot = {"name": agent.name, "identity_key": agent.identity_key, "status": agent.status,
                "department": agent.department}
    db.execute(delete(AgentPermission).where(AgentPermission.agent_id == agent.id))
    db.execute(delete(AgentTool).where(AgentTool.agent_id == agent.id))
    db.delete(agent)
    audit.record(
        db, "agent.delete", request=request, actor=actor, target_type="agent", target_id=agent.id, details=snapshot
    )
    db.commit()


# --- Arrêt d'urgence -----------------------------------------------------------


def _set_emergency(db: Session, actor: User, active: bool) -> None:
    value = {"active": active, "at": utcnow().isoformat(), "by": actor.email}
    row = db.get(SystemSetting, EMERGENCY_KEY)
    if row:
        row.value = value
        row.updated_by = actor.id
    else:
        db.add(SystemSetting(key=EMERGENCY_KEY, value=value, updated_by=actor.id))


def emergency_stop(db: Session, actor: User, request: Request) -> int:
    """Suspend tous les agents ACTIVE et bloque toute (re)activation jusqu'à la levée par un SUPER_ADMIN."""
    active_agents = db.scalars(select(Agent).where(Agent.status == "ACTIVE")).all()
    for agent in active_agents:
        agent.status = "PAUSED"
        audit.record(
            db, "agent.status", request=request, actor=actor, target_type="agent", target_id=agent.id,
            details={"from": "ACTIVE", "to": "PAUSED", "reason": "emergency_stop"},
        )
    _set_emergency(db, actor, True)
    audit.record(
        db, "agent.emergency_stop", request=request, actor=actor, target_type="system",
        details={"paused_agents": len(active_agents)},
    )
    db.commit()
    return len(active_agents)


def emergency_release(db: Session, actor: User, request: Request) -> None:
    """Lève le blocage. Les agents restent PAUSED : chacun doit être repris explicitement."""
    _set_emergency(db, actor, False)
    audit.record(db, "agent.emergency_release", request=request, actor=actor, target_type="system")
    db.commit()
