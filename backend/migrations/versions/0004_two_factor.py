"""2FA TOTP et codes de secours

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-19
"""
import sqlalchemy as sa
from alembic import op

from app.core.db import UTCDateTime

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("two_factor_last_step", sa.BigInteger(), nullable=True))
    op.create_table(
        "recovery_codes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("used_at", UTCDateTime(), nullable=True),
    )
    op.create_index("ix_recovery_codes_user", "recovery_codes", ["user_id"])


def downgrade() -> None:
    op.drop_table("recovery_codes")
    op.drop_column("users", "two_factor_last_step")
