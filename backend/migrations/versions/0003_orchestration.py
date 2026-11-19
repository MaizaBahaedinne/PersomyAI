"""Orchestrateur: missions, tasks, task_runs

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-19
"""
import sqlalchemy as sa
from alembic import op

from app.core.db import UTCDateTime

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "missions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint("status IN ('OPEN','DONE','CANCELLED')", name="ck_missions_status"),
    )
    op.create_index("ix_missions_status", "missions", ["status"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mission_id", sa.Uuid(), sa.ForeignKey("missions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(8), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("required_scope", sa.String(60), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approval_requested_at", UTCDateTime(), nullable=True),
        sa.Column("decided_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_at", UTCDateTime(), nullable=True),
        sa.Column("decision_reason", sa.String(500), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('OPEN','AWAITING_APPROVAL','APPROVED','RUNNING','DONE','FAILED','REJECTED','CANCELLED')",
            name="ck_tasks_status",
        ),
        sa.CheckConstraint("priority IN ('LOW','NORMAL','HIGH')", name="ck_tasks_priority"),
    )
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_agent_id", "tasks", ["agent_id"])
    op.create_index("ix_tasks_mission_id", "tasks", ["mission_id"])

    op.create_table(
        "task_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("task_id", sa.Uuid(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("error_code", sa.String(60), nullable=True),
        sa.Column("cost_cents", sa.Integer(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("triggered_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", UTCDateTime(), nullable=False),
        sa.Column("finished_at", UTCDateTime(), nullable=True),
        sa.CheckConstraint("status IN ('RUNNING','SUCCESS','FAILED')", name="ck_task_runs_status"),
    )
    op.create_index("ix_task_runs_task_id", "task_runs", ["task_id"])
    op.create_index("ix_task_runs_agent_started", "task_runs", ["agent_id", "started_at"])


def downgrade() -> None:
    op.drop_table("task_runs")
    op.drop_table("tasks")
    op.drop_table("missions")
