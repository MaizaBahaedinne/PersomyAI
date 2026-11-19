import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UTCDateTime, utcnow


class Mission(Base):
    """Objectif regroupant des tâches."""

    __tablename__ = "missions"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN','DONE','CANCELLED')", name="ck_missions_status"),
        Index("ix_missions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="OPEN")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)


class Task(Base):
    """Tâche confiée à un agent. Une tâche sensible ne s'exécute qu'après validation humaine."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint(
            "status IN ('OPEN','AWAITING_APPROVAL','APPROVED','RUNNING','DONE','FAILED','REJECTED','CANCELLED')",
            name="ck_tasks_status",
        ),
        CheckConstraint("priority IN ('LOW','NORMAL','HIGH')", name="ck_tasks_priority"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_agent_id", "agent_id"),
        Index("ix_tasks_mission_id", "mission_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("missions.id", ondelete="SET NULL"), nullable=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    priority: Mapped[str] = mapped_column(String(8), nullable=False, default="NORMAL")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    # Permission d'agent exigée pour exécuter la tâche (catalogue `agents.catalog.SCOPES`).
    required_scope: Mapped[str | None] = mapped_column(String(60), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approval_requested_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow, onupdate=utcnow)


class TaskRun(Base):
    """Une tentative d'exécution (compte dans le quota quotidien de l'agent et dans son budget mensuel)."""

    __tablename__ = "task_runs"
    __table_args__ = (
        CheckConstraint("status IN ('RUNNING','SUCCESS','FAILED')", name="ck_task_runs_status"),
        Index("ix_task_runs_task_id", "task_id"),
        Index("ix_task_runs_agent_started", "agent_id", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="RUNNING")
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    cost_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
