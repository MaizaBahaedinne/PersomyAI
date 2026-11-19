import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.agents import service
from app.modules.agents.schemas import (
    AgentCreate,
    AgentOut,
    AgentPage,
    AgentUpdate,
    CatalogOut,
    EmergencyOut,
    ScopesUpdate,
    StatusChange,
    ToolsUpdate,
    build_catalog,
)
from app.modules.audit import service as audit
from app.modules.audit.schemas import AuditPage
from app.modules.authentication.deps import AuthContext, require_permission
from app.modules.permissions.policy import Permission

router = APIRouter(prefix="/agents", tags=["agents"])

Read = Depends(require_permission(Permission.AGENTS_READ))
Write = Depends(require_permission(Permission.AGENTS_WRITE))
Grant = Depends(require_permission(Permission.AGENTS_GRANT))
Delete = Depends(require_permission(Permission.AGENTS_DELETE))


# Routes statiques déclarées avant /{agent_id} pour éviter toute capture.
@router.get("/catalog", response_model=CatalogOut)
def catalog(ctx: AuthContext = Read):
    return build_catalog()


@router.get("/emergency-stop", response_model=EmergencyOut)
def emergency_status(ctx: AuthContext = Read, db: Session = Depends(get_db)):
    return EmergencyOut(**service.emergency_state(db))


@router.post("/emergency-stop", response_model=EmergencyOut)
def emergency_stop(request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)):
    paused = service.emergency_stop(db, ctx.user, request)
    return EmergencyOut(**service.emergency_state(db), paused_agents=paused)


@router.delete("/emergency-stop", response_model=EmergencyOut)
def emergency_release(request: Request, ctx: AuthContext = Grant, db: Session = Depends(get_db)):
    service.emergency_release(db, ctx.user, request)
    return EmergencyOut(**service.emergency_state(db))


@router.get("", response_model=AgentPage)
def list_agents(
    search: Optional[str] = Query(default=None, max_length=100),
    status: Optional[str] = Query(default=None, pattern="^(DRAFT|ACTIVE|PAUSED|ERROR|DISABLED)$"),
    department: Optional[str] = Query(default=None, max_length=40),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Read,
    db: Session = Depends(get_db),
):
    items, total = service.list_agents(
        db, search=search, status=status, department=department, limit=limit, offset=offset
    )
    return AgentPage(items=items, total=total, limit=limit, offset=offset)


@router.post("", response_model=AgentOut, status_code=201)
def create_agent(payload: AgentCreate, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)):
    return service.to_out(db, service.create_agent(db, ctx.user, payload, request))


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: uuid.UUID, ctx: AuthContext = Read, db: Session = Depends(get_db)):
    return service.to_out(db, service.get_agent(db, agent_id))


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: uuid.UUID, payload: AgentUpdate, request: Request, ctx: AuthContext = Write, db: Session = Depends(get_db)
):
    agent = service.get_agent(db, agent_id)
    return service.to_out(db, service.update_agent(db, ctx.user, agent, payload, request))


@router.post("/{agent_id}/status", response_model=AgentOut)
def change_status(
    agent_id: uuid.UUID,
    payload: StatusChange,
    request: Request,
    ctx: AuthContext = Write,
    db: Session = Depends(get_db),
):
    agent = service.get_agent(db, agent_id)
    return service.to_out(db, service.change_status(db, ctx.user, agent, payload.status, payload.reason, request))


@router.put("/{agent_id}/permissions", response_model=AgentOut)
def set_permissions(
    agent_id: uuid.UUID,
    payload: ScopesUpdate,
    request: Request,
    ctx: AuthContext = Grant,
    db: Session = Depends(get_db),
):
    agent = service.get_agent(db, agent_id)
    service.set_permissions(db, ctx.user, agent, payload.permissions, request)
    return service.to_out(db, agent)


@router.put("/{agent_id}/tools", response_model=AgentOut)
def set_tools(
    agent_id: uuid.UUID, payload: ToolsUpdate, request: Request, ctx: AuthContext = Grant, db: Session = Depends(get_db)
):
    agent = service.get_agent(db, agent_id)
    service.set_tools(db, ctx.user, agent, payload.tools, request)
    return service.to_out(db, agent)


@router.post("/{agent_id}/revoke-access", response_model=AgentOut)
def revoke_access(agent_id: uuid.UUID, request: Request, ctx: AuthContext = Grant, db: Session = Depends(get_db)):
    agent = service.get_agent(db, agent_id)
    return service.to_out(db, service.revoke_access(db, ctx.user, agent, request))


@router.delete("/{agent_id}", status_code=204)
def delete_agent(agent_id: uuid.UUID, request: Request, ctx: AuthContext = Delete, db: Session = Depends(get_db)):
    agent = service.get_agent(db, agent_id)
    service.delete_agent(db, ctx.user, agent, request)
    return Response(status_code=204)


@router.get("/{agent_id}/history", response_model=AuditPage)
def history(
    agent_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Read,
    db: Session = Depends(get_db),
):
    service.get_agent(db, agent_id)
    items, total = audit.list_events(db, target_type="agent", target_id=str(agent_id), limit=limit, offset=offset)
    return AuditPage(items=items, total=total, limit=limit, offset=offset)
