"""Celery tasks for the CI research pipeline (SPEC.md §6).

``execute_research_job`` drives the Phase 3 LangGraph graph:

* transitions ``research_jobs.status`` through the SPEC lifecycle
  (planning -> retrieving -> verifying -> synthesizing -> completed|failed),
* publishes progress events to ``job_progress:{job_id}`` as each node runs,
* persists the final battlecard and marks the job completed.

The task is safe for at-least-once delivery: a re-delivered execution
first re-checks the job row and skips jobs that are already terminal.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.agents.ci_graph import build_ci_graph
from app.agents.nodes import reset_progress_hook, set_progress_hook
from app.database import AsyncSessionFactory, dispose_engine
from app.core.redis_client import close_redis
from app.models import Battlecard, ResearchJob, ResearchJobStatus
from app.worker.celery_app import celery_app
from app.worker.progress import ProgressPublisher

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = (ResearchJobStatus.COMPLETED, ResearchJobStatus.FAILED)

#: Maps the step names emitted by agent nodes onto DB status values so the
#: ``research_jobs.status`` column tracks the live pipeline position.
_STEP_TO_STATUS = {
    "planning": ResearchJobStatus.PLANNING,
    "retrieving": ResearchJobStatus.RETRIEVING,
    "verifying": ResearchJobStatus.VERIFYING,
    "synthesizing": ResearchJobStatus.SYNTHESIZING,
}


@celery_app.task(
    name="app.worker.tasks.execute_research_job",
    acks_late=True,
    max_retries=3,
    default_retry_delay=15,
    retry_backoff=True,
    autoretry_for=(TimeoutError, OSError, ConnectionError),
)
def execute_research_job(
    job_id: str,
    target: str,
    competitor: str,
    user_id: str,
) -> dict:
    """Celery entrypoint; runs the research graph in a fresh event loop.

    Transport-level failures (broker/network) are auto-retried by Celery;
    application errors are surfaced once and the job is marked ``failed``.
    """
    async def run_and_cleanup():
        try:
            return await _run_research_job(job_id, target, competitor, user_id)
        finally:
            # Each Celery invocation creates a new loop. Do not carry pooled
            # asyncpg/Redis connections into the next task's event loop.
            try:
                await close_redis()
            finally:
                await dispose_engine()

    return asyncio.run(run_and_cleanup())


def _seed_state(target: str, competitor: str) -> dict:
    """Graph input matching the SPEC §5 ``CIState`` channels."""
    return {
        "target": target,
        "competitor": competitor,
        "sub_queries": [],
        "scraped_content": [],
        "verified_corpus": "",
        "validation_flags": {},
        "retries": 0,
        "is_valid": False,
        "final_output": {},
    }


async def _set_job_status(
    job_id: str,
    status_enum: ResearchJobStatus,
    *,
    error: Optional[str] = None,
    completed_at: bool = False,
) -> None:
    """Persist a job status transition (best effort on missing rows)."""
    try:
        async with AsyncSessionFactory() as session:
            row = await session.get(ResearchJob, uuid.UUID(job_id))
            if row is None:
                logger.error("job %s not found while setting %s", job_id, status_enum)
                return
            row.status = status_enum
            if error is not None:
                row.error_log = error[:4000]
            if completed_at:
                row.completed_at = datetime.now(timezone.utc)
            await session.commit()
    except Exception:
        logger.exception("failed to persist status %s for job %s", status_enum, job_id)
        raise


async def _save_battlecard(
    job_id: str,
    user_id: str,
    target: str,
    competitor: str,
    report_data: dict[str, Any],
) -> uuid.UUID:
    """Persist the final battlecard and return its id."""
    async with AsyncSessionFactory() as session:
        battlecard = Battlecard(
            job_id=uuid.UUID(job_id),
            user_id=uuid.UUID(user_id),
            target_company=target,
            competitor=competitor,
            report_data=report_data,
        )
        session.add(battlecard)
        await session.commit()
        await session.refresh(battlecard)
        return battlecard.id


async def _run_research_job(
    job_id: str,
    target: str,
    competitor: str,
    user_id: str,
) -> dict[str, Any]:
    """Async body of :func:`execute_research_job`."""
    publisher = ProgressPublisher(job_id)

    try:
        # --- Guard: skip missing / already-terminal jobs (re-delivery). ---
        async with AsyncSessionFactory() as session:
            job = await session.get(ResearchJob, uuid.UUID(job_id))
            if job is None:
                logger.error("research job %s not found in DB", job_id)
                return {"job_id": job_id, "status": "missing"}
            if job.status in _TERMINAL_STATUSES:
                logger.warning(
                    "research job %s already terminal (%s); skipping",
                    job_id,
                    job.status,
                )
                return {"job_id": job_id, "status": str(job.status)}
            job.status = ResearchJobStatus.PLANNING
            job.error_log = None
            await session.commit()

        await publisher.publish(
            "planning", f"Planning research for {target} vs {competitor}"
        )

        # --- Run the compiled Phase 3 graph, streaming each node step. ---
        async def _progress_hook(step: str, message: str) -> None:
            await publisher.publish(step, message)
            status_enum = _STEP_TO_STATUS.get(step)
            if status_enum is not None:
                await _set_job_status(job_id, status_enum)

        token = set_progress_hook(_progress_hook)
        try:
            graph = build_ci_graph()
            state = await graph.ainvoke(_seed_state(target, competitor))
        finally:
            reset_progress_hook(token)

        final_output = dict(state.get("final_output") or {})
        if not final_output:
            raise RuntimeError(
                "graph completed without a final_output payload"
            )

        # --- Persist results and complete the job. ---
        battlecard_id = await _save_battlecard(
            job_id, user_id, target, competitor, final_output
        )
        await _set_job_status(
            job_id, ResearchJobStatus.COMPLETED, completed_at=True
        )
        await publisher.publish(
            "completed",
            "Battlecard ready",
            {"battlecard_id": str(battlecard_id)},
        )
        logger.info(
            "job %s completed (battlecard %s)",
            job_id,
            battlecard_id,
        )
        return {
            "job_id": job_id,
            "battlecard_id": str(battlecard_id),
            "status": "completed",
        }

    except Exception as exc:  # noqa: BLE001 - job failure must be persisted
        logger.exception("research job %s failed", job_id)
        try:
            await _set_job_status(
                job_id,
                ResearchJobStatus.FAILED,
                error=f"{type(exc).__name__}: {exc}",
            )
        except Exception:
            logger.exception("could not persist failure state for job %s", job_id)
            raise
        try:
            await publisher.publish("failed", "Research job failed", {"error": str(exc)})
        except Exception:
            logger.exception("could not publish failure event for job %s", job_id)
        raise
