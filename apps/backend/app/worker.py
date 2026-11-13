"""Worker process: schedules synchronisation and sweeps abandoned runs.

Run with ``python -m app.worker``. It refuses to start when scheduling is disabled or no
provider token is configured, because a "successful" no-op would hide a broken setup.
"""

from __future__ import annotations

import logging
import signal
import sys

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.database.session import init_engine
from app.ingestion.provider_factory import create_provider_runtime
from app.sync.engine import SyncEngine, mark_stale_running_runs
from app.sync.scheduler import build_scheduler

logger = logging.getLogger(__name__)


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)

    if not settings.sync_enabled:
        logger.error(
            "scheduler is disabled; set SYNC_ENABLED=true to run the worker",
            extra={"event": "worker.disabled", "component": "worker"},
        )
        return 2

    if not settings.provider_configured:
        logger.error(
            "no provider token configured; refusing to start the worker",
            extra={"event": "worker.no_provider", "component": "worker"},
        )
        return 2

    init_engine(settings)

    try:
        stale = mark_stale_running_runs(settings=settings)
        runtime = create_provider_runtime(settings)
    except AppError as exc:
        logger.error(
            "worker startup failed",
            extra={"event": "worker.startup_failed", "component": "worker"},
        )
        logger.error(str(exc))
        return 2

    if stale:
        logger.warning(
            "marked abandoned synchronisation runs as failed",
            extra={"event": "worker.stale_runs", "component": "worker"},
        )

    engine = SyncEngine(
        settings=settings,
        provider_id=runtime.provider_id,
        adapter=runtime.adapter,
    )
    scheduler = build_scheduler(engine, settings)

    def _shutdown(signum, _frame) -> None:
        logger.info(
            "worker shutting down",
            extra={"event": "worker.shutdown", "component": "worker"},
        )
        scheduler.shutdown(wait=False)
        runtime.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    scheduler.start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
