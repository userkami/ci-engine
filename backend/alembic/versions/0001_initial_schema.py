"""initial schema: users, user_credits, research_jobs, battlecards

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-11

Mirrors SPEC.md section 4 exactly (column names, types, defaults, CHECK
constraints and FK cascade behaviour).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels = None
depends_on = None

#: Native PostgreSQL UUID column type (maps from sa.Uuid / python uuid.UUID).
UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # pgvector extension ships with the pgvector/pgvector:pg16 image.
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_credits",
        sa.Column(
            "user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "balance",
            sa.Integer(),
            server_default=sa.text("5"),
            nullable=False,
        ),
        sa.Column(
            "tier",
            sa.String(50),
            server_default=sa.text("'free'"),
            nullable=False,
        ),
        sa.Column("stripe_customer_id", sa.String(100), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "balance >= 0",
            name="ck_user_credits_balance_non_negative",
        ),
        sa.CheckConstraint(
            "tier IN ('free', 'starter', 'growth')",
            name="ck_user_credits_tier_valid",
        ),
    )

    op.create_table(
        "research_jobs",
        sa.Column(
            "id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_company", sa.String(100), nullable=False),
        sa.Column("competitor", sa.String(100), nullable=False),
        sa.Column(
            "status",
            sa.String(50),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column(
            "cost_credits",
            sa.Integer(),
            server_default=sa.text("5"),
            nullable=False,
        ),
        sa.Column("error_log", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'planning', 'retrieving', 'verifying', "
            "'synthesizing', 'completed', 'failed')",
            name="ck_research_jobs_status_valid",
        ),
        sa.CheckConstraint(
            "cost_credits >= 0",
            name="ck_research_jobs_cost_credits_non_negative",
        ),
    )
    op.create_index("ix_research_jobs_user_id", "research_jobs", ["user_id"])

    op.create_table(
        "battlecards",
        sa.Column(
            "id",
            UUID,
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "job_id",
            UUID,
            sa.ForeignKey("research_jobs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_company", sa.String(100), nullable=False),
        sa.Column("competitor", sa.String(100), nullable=False),
        sa.Column("report_data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index("ix_battlecards_user_id", "battlecards", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_battlecards_user_id", table_name="battlecards")
    op.drop_table("battlecards")
    op.drop_index("ix_research_jobs_user_id", table_name="research_jobs")
    op.drop_table("research_jobs")
    op.drop_table("user_credits")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.execute('DROP EXTENSION IF EXISTS "vector"')