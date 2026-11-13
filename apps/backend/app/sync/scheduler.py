"""APScheduler wiring for a single worker process.

The scheduler is disabled unless ``SYNC_ENABLED=true``. It uses one worker thread so two
job types can never run at once: SQLite has one writer and the provider has one rate
limit, and both are process-wide assumptions (ADR-0007).
"""

from __future__ import annotations

import logging
from typing import Callable

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import Settings
from app.sync.engine import SyncEngine, SyncRunSummary
from app.sync.jobs import (
    sync_competition_details,
    sync_competitions,
    sync_fixtures,
    sync_results,
    sync_statistics,
    sync_teams,
)

logger = logging.getLogger(__name__)

JOB_HANDLERS: dict[str, Callable] = {
    "competitions": sync_competitions,
    "competition_details": sync_competition_details,
    "teams": sync_teams,
    "fixtures": sync_fixtures,
    "results": sync_results,
    "statistics": sync_statistics,
}


def run_named_job(engine: SyncEngine, job_type: str) -> SyncRunSummary:
    handler = JOB_HANDLERS.get(job_type)
    if handler is None:
        raise ValueError(f"unknown sync job type: {job_type}")
    return engine.run(job_type=job_type, handler=handler)


def build_scheduler(engine: SyncEngine, settings: Settings) -> BlockingScheduler:
    """Register conservative periodic jobs, all on one worker thread."""

    scheduler = BlockingScheduler(
        timezone="UTC",
        executors={"default": ThreadPoolExecutor(max_workers=1)},
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,
        },
    )

    interval = settings.sync_interval_minutes
    scheduler.add_job(
        run_named_job,
        trigger=IntervalTrigger(minutes=interval),
        args=[engine, "fixtures"],
        id="sync_fixtures",
        name="Sync fixtures and results window",
    )
    scheduler.add_job(
        run_named_job,
        trigger=IntervalTrigger(minutes=max(5, interval // 4)),
        args=[engine, "results"],
        id="sync_results",
        name="Sync final results",
    )
    scheduler.add_job(
        run_named_job,
        trigger=IntervalTrigger(minutes=max(15, interval)),
        args=[engine, "statistics"],
        id="sync_statistics",
        name="Sync available match statistics",
    )
    return scheduler
