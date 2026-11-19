"""Importe tous les modèles pour que les métadonnées SQLAlchemy soient complètes."""

from app.core.db import Base
from app.modules.agents.models import Agent, AgentPermission, AgentTool
from app.modules.audit.models import AuditEvent
from app.modules.authentication.models import AuthSession, LoginAttempt
from app.modules.orchestration.models import Mission, Task, TaskRun
from app.modules.settings.models import SystemSetting
from app.modules.users.models import User

__all__ = [
    "Base",
    "Agent",
    "AgentPermission",
    "AgentTool",
    "AuditEvent",
    "AuthSession",
    "LoginAttempt",
    "Mission",
    "SystemSetting",
    "Task",
    "TaskRun",
    "User",
]
