"""Pydantic DTOs for the public HTTP API (SPEC.md §6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JobCreateRequest(BaseModel):
    """Request body for ``POST /api/jobs/create``."""

    target_company: str = Field(..., min_length=1, max_length=100)
    competitor: str = Field(..., min_length=1, max_length=100)


class JobCreateResponse(BaseModel):
    """Response body for ``POST /api/jobs/create``."""

    job_id: uuid.UUID
    status: str


class ProgressEvent(BaseModel):
    """Single SSE payload published to ``job_progress:{job_id}``.

    ``msg`` mirrors ``message`` for the BUILD_GUIDE Phase 4 payload shape;
    ``data`` carries optional extra state (e.g. the battlecard id).
    """

    step: str
    message: str
    msg: str = ""
    data: Any = None


class BattlecardResponse(BaseModel):
    """Serialised ``battlecards`` row returned by the public API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    user_id: uuid.UUID
    target_company: str
    competitor: str
    report_data: dict[str, Any]
    created_at: datetime


class OAuthProvisionRequest(BaseModel):
    """Body for ``POST /api/auth/provision`` (Phase 5 identity handshake).

    Called by the Next.js server after a verified Google session; never
    exposed to end-user browsers directly.
    """

    email: str = Field(..., min_length=3, max_length=255)
    name: str | None = None
    image_url: str | None = None


class OAuthProvisionResponse(BaseModel):
    """Issued backend token + profile state returned to the frontend."""

    access_token: str
    user_id: uuid.UUID
    email: str
    balance: int