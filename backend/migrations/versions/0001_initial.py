"""Initial schema: users, auth_sessions, login_attempts, audit_events, system_settings

Revision ID: 0001
Revises:
Create Date: 2026-11-19
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.core.db import UTCDateTime

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

JSONType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("preferred_language", sa.String(5), nullable=False),
        sa.Column("two_factor_enabled", sa.Boolean(), nullable=False),
        sa.Column("two_factor_secret_encrypted", sa.String(255), nullable=True),
        sa.Column("last_login_at", UTCDateTime(), nullable=True),
        sa.Column("password_changed_at", UTCDateTime(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint("role IN ('SUPER_ADMIN','ADMIN','OPERATOR','VIEWER')", name="ck_users_role"),
        sa.CheckConstraint("preferred_language IN ('fr','en')", name="ck_users_language"),
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("last_seen_at", UTCDateTime(), nullable=False),
        sa.Column("expires_at", UTCDateTime(), nullable=False),
        sa.Column("revoked_at", UTCDateTime(), nullable=True),
    )
    op.create_index("ix_auth_sessions_user_active", "auth_sessions", ["user_id", "revoked_at"])

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
    )
    op.create_index("ix_login_attempts_email_created", "login_attempts", ["email", "created_at"])
    op.create_index("ix_login_attempts_ip_created", "login_attempts", ["ip_address", "created_at"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_label", sa.String(320), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(60), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("details", JSONType, nullable=True),
    )
    op.create_index("ix_audit_events_created", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_actor", "audit_events", ["actor_user_id"])

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("value", JSONType, nullable=True),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("audit_events")
    op.drop_table("login_attempts")
    op.drop_table("auth_sessions")
    op.drop_table("users")
