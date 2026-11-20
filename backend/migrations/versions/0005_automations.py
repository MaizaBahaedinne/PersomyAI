"""Automatisations

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-20
"""

import sqlalchemy as sa
from alembic import op

from app.core.db import UTCDateTime

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "automations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("trigger_type", sa.String(40), nullable=False),
        sa.Column("trigger_config", sa.JSON(), nullable=False),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("anti_loop_key", sa.String(120), nullable=True),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
        sa.Column("last_triggered_at", UTCDateTime(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint("status IN ('DRAFT','ACTIVE','PAUSED')", name="ck_automations_status"),
    )
    op.create_index("ix_automations_status", "automations", ["status"])
    op.create_index("ix_automations_trigger_type", "automations", ["trigger_type"])


def downgrade() -> None:
    op.drop_index("ix_automations_trigger_type", table_name="automations")
    op.drop_index("ix_automations_status", table_name="automations")
    op.drop_table("automations")
