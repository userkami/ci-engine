"""SQLAlchemy ORM models for the Competitive Intelligence platform.

Schema follows SPEC.md section 4 (PostgreSQL + pgvector). Table names,
column names, types, enumerate values and constraints documented there are
canonical — do not introduce alternate naming conventions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CreditTier(StrEnum):
    """Allowed values for :attr:`UserCredit.tier` (SPEC.md §4)."""

    FREE = "free"
    STARTER = "starter"
    GROWTH = "growth"


class ResearchJobStatus(StrEnum):
    """Allowed values for :attr:`ResearchJob.status` (SPEC.md §4)."""

    QUEUED = "queued"
    PLANNING = "planning"
    RETRIEVING = "retrieving"
    VERIFYING = "verifying"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


#: Credit cost of a single research job (SPEC.md §4 / BUILD_GUIDE Phase 4).
JOB_COST_CREDITS = 5


def uuid_pk() -> Mapped[uuid.UUID]:
    """Primary key column: native PostgreSQL UUID, generated client-side."""
    return mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


def created_at() -> Mapped[datetime]:
    """Standard ``created_at`` TIMESTAMPTZ column."""
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()

    credits: Mapped["UserCredit"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    research_jobs: Mapped[list["ResearchJob"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    battlecards: Mapped[list["Battlecard"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserCredit(Base):
    __tablename__ = "user_credits"
    __table_args__ = (
        CheckConstraint(
            "balance >= 0", name="ck_user_credits_balance_non_negative"
        ),
        CheckConstraint(
            "tier IN ('free', 'starter', 'growth')",
            name="ck_user_credits_tier_valid",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    balance: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default=text("5")
    )
    tier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=CreditTier.FREE,
        server_default=text("'free'"),
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="credits")


class ResearchJob(Base):
    __tablename__ = "research_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'planning', 'retrieving', 'verifying', "
            "'synthesizing', 'completed', 'failed')",
            name="ck_research_jobs_status_valid",
        ),
        CheckConstraint(
            "cost_credits >= 0", name="ck_research_jobs_cost_credits_non_negative"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_company: Mapped[str] = mapped_column(String(100), nullable=False)
    competitor: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ResearchJobStatus.QUEUED,
        server_default=text("'queued'"),
    )
    cost_credits: Mapped[int] = mapped_column(
        Integer, nullable=False, default=JOB_COST_CREDITS, server_default=text("5")
    )
    error_log: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at()
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="research_jobs")
    battlecard: Mapped["Battlecard"] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )


class Battlecard(Base):
    __tablename__ = "battlecards"

    id: Mapped[uuid.UUID] = uuid_pk()
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_jobs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_company: Mapped[str] = mapped_column(String(100), nullable=False)
    competitor: Mapped[str] = mapped_column(String(100), nullable=False)
    report_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = created_at()

    job: Mapped[ResearchJob] = relationship(back_populates="battlecard")
    user: Mapped[User] = relationship(back_populates="battlecards")


class RuntimeConfig(Base):
    """Key-value store for runtime configuration overrides.

    Values stored here take precedence over environment variables and are
    read at call time, so changes take effect immediately without restart.
    Used by the admin configuration UI to manage model selection and API keys.
    """

    __tablename__ = "runtime_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )