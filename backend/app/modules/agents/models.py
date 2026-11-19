import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime, utcnow
from app.modules.audit.models import JSONType


class Agent(Base):
    """Identité technique d'un agent IA. Un agent n'a ni mot de passe, ni session, ni ligne dans `users`."""

    __tablename__ = "agents"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','ACTIVE','PAUSED','ERROR','DISABLED')", name="ck_agents_status"),
        CheckConstraint("autonomy_level BETWEEN 1 AND 3", name="ck_agents_autonomy"),
        CheckConstraint("max_actions_per_day >= 0", name="ck_agents_max_actions"),
        CheckConstraint("monthly_budget_cents >= 0", name="ck_agents_budget"),
        Index("ix_agents_status", "status"),
        Index("ix_agents_department", "department"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    identity_key: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    department: Mapped[str] = mapped_column(String(40), nullable=False)
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    mission: Mapped[str] = mapped_column(Text, nullable=False, default="")
    skills: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    autonomy_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    config: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    max_actions_per_day: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    # 0 = aucun appel IA payant autorisé.
    monthly_budget_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    access_revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)


class AgentPermission(Base):
    __tablename__ = "agent_permissions"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    permission: Mapped[str] = mapped_column(String(60), primary_key=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)


class AgentTool(Base):
    __tablename__ = "agent_tools"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True
    )
    tool: Mapped[str] = mapped_column(String(60), primary_key=True)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
