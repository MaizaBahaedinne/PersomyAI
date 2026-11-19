"""Agents IA: agents, agent_permissions, agent_tools

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db import UTCDateTime

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("identity_key", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("department", sa.String(40), nullable=False),
        sa.Column("role", sa.String(120), nullable=False),
        sa.Column("mission", sa.Text(), nullable=False),
        sa.Column("skills", JSONType, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("autonomy_level", sa.Integer(), nullable=False),
        sa.Column("config", JSONType, nullable=False),
        sa.Column("max_actions_per_day", sa.Integer(), nullable=False),
        sa.Column("monthly_budget_cents", sa.Integer(), nullable=False),
        sa.Column("access_revoked_at", UTCDateTime(), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','PAUSED','ERROR','DISABLED')", name="ck_agents_status"),
        sa.CheckConstraint("autonomy_level BETWEEN 1 AND 3", name="ck_agents_autonomy"),
        sa.CheckConstraint("max_actions_per_day >= 0", name="ck_agents_max_actions"),
        sa.CheckConstraint("monthly_budget_cents >= 0", name="ck_agents_budget"),
    )
    op.create_index("ix_agents_status", "agents", ["status"])
    op.create_index("ix_agents_department", "agents", ["department"])

    op.create_table(
        "agent_permissions",
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission", sa.String(60), primary_key=True),
        sa.Column("granted_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
    )

    op.create_table(
        "agent_tools",
        sa.Column("agent_id", sa.Uuid(), sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tool", sa.String(60), primary_key=True),
        sa.Column("granted_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_tools")
    op.drop_table("agent_permissions")
    op.drop_index("ix_agents_department", table_name="agents")
    op.drop_index("ix_agents_status", table_name="agents")
    op.drop_table("agents")
