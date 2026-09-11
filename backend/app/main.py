"""FastAPI application: job dispatch, SSE streaming, battlecard retrieval.

Endpoints (SPEC.md §6):
    POST /api/jobs/create            atomic credit deduction -> job -> Celery
    GET  /api/jobs/{job_id}/stream   SSE progress (Redis Pub/Sub + DB fallback)
    GET  /api/battlecards/{id}       saved battlecard JSON
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.redis_client import close_redis, get_redis
from app.core.security import create_access_token, get_current_user
from app.database import AsyncSessionFactory, dispose_engine, get_db
from app.models import (
    JOB_COST_CREDITS,
    Battlecard,
    ResearchJob,
    ResearchJobStatus,
    User,
    UserCredit,
)
from app.schemas import (
    BattlecardResponse,
    JobCreateRequest,
    JobCreateResponse,
    OAuthProvisionRequest,
    OAuthProvisionResponse,
)
from app.services.credit_service import deduct_credits, restore_credits
from app.worker.tasks import execute_research_job

logger = logging.getLogger(__name__)

_SETTINGS = get_settings()

SSE_POLL_INTERVAL = 2.0          # DB poll cadence when Redis / job quiet
SSE_HEARTBEAT_EVERY = 15         # steps between keep-alive comments
_TERMINAL_MESSAGES = {
    "completed": "Battlecard ready",
    "failed": "Research job failed",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Release pooled connections on shutdown (used by uvicorn workers)."""
    yield
    await dispose_engine()
    await close_redis()


app = FastAPI(
    title="CI Backend",
    version="0.1.0",
    description="Autonomous B2B Competitive Intelligence engine API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        o.strip()
        for o in _SETTINGS.cors_origins.split(",")
        if o.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    """Liveness probe for Coolify/uptime monitors (also pings Redis)."""
    redis_ok = False
    try:
        client = await get_redis()
        redis_ok = bool(await client.ping())
    except Exception:
        redis_ok = False
    return {"status": "ok" if redis_ok else "degraded", "redis": redis_ok}


# --------------------------------------------------------------------------- #
# POST /api/auth/provision  (Phase 5 identity handshake)
# --------------------------------------------------------------------------- #
@app.post(
    "/api/auth/provision",
    response_model=OAuthProvisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def provision_oauth_user(
    body: OAuthProvisionRequest,
    db: AsyncSession = Depends(get_db),
) -> OAuthProvisionResponse:
    """Idempotently upsert a Google-verified user and credit profile.

    Called by the Next.js server (never directly by browsers) after a
    NextAuth session is established. Returns a short-lived backend JWT the
    frontend uses for subsequent protected calls.
    """
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid email is required",
        )

    try:
        user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
    except Exception:
        await db.rollback()
        raise

    created_user = user is None
    if created_user:
        user = User(email=email, name=body.name, image_url=body.image_url)
        db.add(user)
    else:
        if body.name:
            user.name = body.name
        if body.image_url:
            user.image_url = body.image_url

    try:
        await db.commit()
        await db.refresh(user)
    except IntegrityError:
        # Race: another request created the same email — re-read it.
        await db.rollback()
        user = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one()
        created_user = False

    # Ensure the default credit profile exists (SPEC §4: balance 5).
    credits = await db.get(UserCredit, user.id)
    if credits is None:
        credits = UserCredit(user_id=user.id, balance=5)
        db.add(credits)
        try:
            await db.commit()
            await db.refresh(credits)
        except IntegrityError:
            await db.rollback()
            credits = await db.get(UserCredit, user.id)

    access_token = create_access_token(str(user.id))
    return OAuthProvisionResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email,
        balance=credits.balance if credits else 5,
    )


# --------------------------------------------------------------------------- #
# POST /api/jobs/create
# --------------------------------------------------------------------------- #
@app.post(
    "/api/jobs/create",
    response_model=JobCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_job(
    body: JobCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobCreateResponse:
    """Atomically deduct credits, create the job row, dispatch to Celery.

    Failure handing:
    * insufficient credits        -> 402, nothing persists,
    * job-row insert failure      -> the deduction is refunded,
    * broker unavailable          -> job marked failed + credits refunded.
    """
    target = body.target_company.strip()
    competitor = body.competitor.strip()

    # 1) Atomic credit deduction (pessimistic row lock, SPEC §4/§6).
    if not await deduct_credits(db, user.id, JOB_COST_CREDITS):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits or no credit profile",
        )

    # 2) Persist the queued job.
    job = ResearchJob(
        user_id=user.id,
        target_company=target,
        competitor=competitor,
        status=ResearchJobStatus.QUEUED,
        cost_credits=JOB_COST_CREDITS,
    )
    db.add(job)
    try:
        await db.commit()
        await db.refresh(job)
    except Exception:
        await db.rollback()
        await _refund_credits(user.id, JOB_COST_CREDITS)
        raise

    # 3) Dispatch to the Celery worker (async, off the event loop).
    try:
        await asyncio.to_thread(
            execute_research_job.delay,
            str(job.id),
            target,
            competitor,
            str(user.id),
        )
    except Exception as exc:
        logger.exception("failed to enqueue research job %s", job.id)
        job.status = ResearchJobStatus.FAILED
        job.error_log = f"dispatch failed: {type(exc).__name__}: {exc}"
        try:
            await db.commit()
        except Exception:
            await db.rollback()
        await _refund_credits(user.id, JOB_COST_CREDITS)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research queue unavailable; credits refunded",
        ) from exc

    return JobCreateResponse(job_id=job.id, status=str(job.status))


async def _refund_credits(user_id: uuid.UUID, amount: int) -> None:
    """Compensate a deduction after a downstream failure (best effort)."""
    try:
        async with AsyncSessionFactory() as session:
            await restore_credits(session, user_id, amount)
    except Exception:
        logger.exception(
            "CRITICAL: failed to refund %s credits to %s", amount, user_id
        )


# --------------------------------------------------------------------------- #
# GET /api/jobs/{job_id}/stream  (Server-Sent Events)
# --------------------------------------------------------------------------- #
def _sse_frame(payload: str) -> str:
    """Wrap a single-line JSON string into an SSE ``data:`` frame."""
    return f"data: {payload}\n\n"


def _progress_payload(step: str, message: str, data: Any = None) -> str:
    """Build the SSE payload (SPEC §6 schema + ``msg`` alias)."""
    return json.dumps(
        {"step": step, "message": message, "msg": message, "data": data},
        default=str,
    )


async def _job_state(job_id: uuid.UUID) -> tuple[str, str]:
    """Return ``(status, error_log)`` for a job (''/'missing' on failure)."""
    try:
        async with AsyncSessionFactory() as session:
            row = await session.get(ResearchJob, job_id)
            if row is None:
                return ("missing", "")
            return (str(row.status), row.error_log or "")
    except Exception:
        logger.exception("DB poll failed for job %s", job_id)
        return ("missing", "")


async def _progress_event_source(job_id: uuid.UUID) -> AsyncGenerator[str, None]:
    """Yield SSE frames until the job reaches a terminal state.

    Primary source: Redis Pub/Sub ``job_progress:{job_id}``. Every idle
    interval polls PostgreSQL so the stream terminates cleanly even when a
    published event (or Redis itself) is lost.
    """
    channel = f"job_progress:{job_id}"

    # Fast path: the job finished before this client subscribed.
    status_now, error_now = await _job_state(job_id)
    if status_now in ("completed", "failed"):
        yield _sse_frame(
            _progress_payload(
                status_now,
                _TERMINAL_MESSAGES[status_now],
                {"error": error_now} if status_now == "failed" else None,
            )
        )
        return

    yield _sse_frame(_progress_payload("queued", f"Job {job_id} queued"))

    pubsub = None
    subscribed = False
    try:
        redis_client = await get_redis()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        subscribed = True
    except Exception as exc:
        logger.warning(
            "Redis Pub/Sub unavailable; SSE will poll the DB: %s", exc
        )
        pubsub = None

    beats_since_heartbeat = 0
    try:
        while True:
            if pubsub is not None:
                try:
                    # Block briefly; falls through to the DB poll on idle.
                    message = await asyncio.wait_for(
                        pubsub.get_message(
                            ignore_subscribe_messages=True, timeout=1.0
                        ),
                        timeout=1.5,
                    )
                except asyncio.TimeoutError:
                    message = None
                except Exception as exc:
                    logger.warning(
                        "Redis stream dropped; SSE will poll the DB: %s", exc
                    )
                    message = None
                    pubsub = None  # permanently fall back to DB polling
                if message:
                    data = message.get("data")
                    if data:
                        payload = (
                            data if isinstance(data, str) else json.dumps(data)
                        )
                        yield _sse_frame(payload)
                        try:
                            step = json.loads(payload).get("step")
                        except Exception:
                            step = None
                        if step in ("completed", "failed"):
                            return
                    continue

            # DB poll path: used when Redis is down, or the channel is idle.
            beats_since_heartbeat += 1
            status_now, error_now = await _job_state(job_id)
            if status_now == "completed":
                yield _sse_frame(
                    _progress_payload(
                        "completed", _TERMINAL_MESSAGES["completed"]
                    )
                )
                return
            if status_now == "failed":
                yield _sse_frame(
                    _progress_payload(
                        "failed",
                        _TERMINAL_MESSAGES["failed"],
                        {"error": error_now},
                    )
                )
                return
            if beats_since_heartbeat % SSE_HEARTBEAT_EVERY == 0:
                yield ": keep-alive\n\n"
            await asyncio.sleep(SSE_POLL_INTERVAL)
    finally:
        if pubsub is not None and subscribed:
            try:
                await pubsub.unsubscribe(channel)
            except Exception:
                logger.warning("could not unsubscribe from %s", channel)


@app.get("/api/jobs/{job_id}/stream")
async def stream_job_progress(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """SSE stream of real-time progress for a research job (SPEC.md §6)."""
    job = await db.get(ResearchJob, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return StreamingResponse(
        _progress_event_source(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/battlecards/{battlecard_id}", response_model=BattlecardResponse)
async def get_battlecard(
    battlecard_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BattlecardResponse:
    """Return the saved battlecard JSON for its owner (SPEC.md §6)."""
    battlecard = await db.get(Battlecard, battlecard_id)
    if battlecard is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Battlecard not found",
        )
    if battlecard.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This battlecard belongs to another user",
        )
    return BattlecardResponse.model_validate(battlecard)