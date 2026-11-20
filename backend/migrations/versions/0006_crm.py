"""CRM companies and contacts

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-20
"""

import sqlalchemy as sa
from alembic import op

from app.core.db import UTCDateTime

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_companies",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False, unique=True),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("website", sa.String(240), nullable=True),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE','ARCHIVED')", name="ck_crm_companies_status"),
    )
    op.create_index("ix_crm_companies_name", "crm_companies", ["name"])
    op.create_index("ix_crm_companies_status", "crm_companies", ["status"])

    op.create_table(
        "crm_contacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("company_id", sa.Uuid(), sa.ForeignKey("crm_companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("first_name", sa.String(120), nullable=False),
        sa.Column("last_name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(40), nullable=True),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.CheckConstraint("status IN ('LEAD','ACTIVE','INACTIVE')", name="ck_crm_contacts_status"),
    )
    op.create_index("ix_crm_contacts_last_name", "crm_contacts", ["last_name"])
    op.create_index("ix_crm_contacts_email", "crm_contacts", ["email"])
    op.create_index("ix_crm_contacts_company", "crm_contacts", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_contacts_company", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_email", table_name="crm_contacts")
    op.drop_index("ix_crm_contacts_last_name", table_name="crm_contacts")
    op.drop_table("crm_contacts")

    op.drop_index("ix_crm_companies_status", table_name="crm_companies")
    op.drop_index("ix_crm_companies_name", table_name="crm_companies")
    op.drop_table("crm_companies")
