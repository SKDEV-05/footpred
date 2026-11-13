"""Operator command line.

Manual synchronisation is a CLI operation because the HTTP API has no authentication in
Phase 3 and therefore no write surface (ADR-0005). Output is JSON so runs can be logged
or diffed by an operator script.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any

from sqlalchemy import desc, select

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.time import utc_now
from app.core.logging import configure_logging
from app.database.session import init_engine, session_scope
from app.ingestion.provider_factory import create_provider_runtime
from app.models.enums import SyncStatus
from app.models.provenance import DataSyncRun
from app.sync.engine import SyncEngine, mark_stale_running_runs, SyncRunSummary
from app.sync.scheduler import JOB_HANDLERS, run_named_job

_EPILOG = """\
Examples:
  python -m app.cli status
  python -m app.cli check-provider
  python -m app.cli sync fixtures
  python -m app.cli sync statistics
  python -m app.cli migrate
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="football-cli",
        description="Football Intelligence Platform operator CLI (Phase 3).",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Show recent synchronisation runs.")
    subparsers.add_parser(
        "check-provider", help="Verify provider configuration with one read request."
    )
    subparsers.add_parser(
        "sweep-runs", help="Mark abandoned running sync runs as failed."
    )

    sync = subparsers.add_parser("sync", help="Run one synchronisation job.")
    sync.add_argument(
        "job",
        choices=sorted(JOB_HANDLERS),
        help="Job type to run once.",
    )

    subparsers.add_parser("migrate", help="Apply database migrations to head.")
    return parser


# -- commands --------------------------------------------------------------------


def _status(settings: Settings) -> tuple[dict[str, Any], int]:
    with session_scope() as session:
        runs = session.execute(
            select(DataSyncRun).order_by(desc(DataSyncRun.started_at)).limit(10)
        ).scalars().all()
        last_success = session.execute(
            select(DataSyncRun)
            .where(DataSyncRun.status == SyncStatus.SUCCESS)
            .order_by(desc(DataSyncRun.finished_at))
            .limit(1)
        ).scalars().first()

    payload = {
        "provider_configured": settings.provider_configured,
        "sync_enabled": settings.sync_enabled,
        "last_successful_sync_at": _iso(last_success.finished_at) if last_success else None,
        "runs": [
            {
                "id": run.id,
                "job_type": run.job_type,
                "status": run.status.value,
                "started_at": _iso(run.started_at),
                "finished_at": _iso(run.finished_at),
                "records_fetched": run.records_fetched,
                "records_created": run.records_created,
                "records_updated": run.records_updated,
                "records_unchanged": run.records_unchanged,
                "records_rejected": run.records_rejected,
                "error_count": run.error_count,
                "error_summary": run.error_summary,
            }
            for run in runs
        ],
    }
    return payload, 0


def _check_provider(settings: Settings) -> tuple[dict[str, Any], int]:
    if not settings.provider_configured:
        return (
            {
                "configured": False,
                "message": (
                    "FOOTBALL_DATA_ORG_TOKEN is not set. Provider calls are refused "
                    "rather than faked."
                ),
            },
            2,
        )

    runtime = create_provider_runtime(settings)
    try:
        fetched = runtime.adapter.fetch_competitions()
        sample = [
            {"external_id": item.external_id, "name": item.name, "code": item.code}
            for item in fetched.items[:5]
        ]
        payload = {
            "configured": True,
            "provider": runtime.adapter.code,
            "competitions_returned": len(fetched.items),
            "raw_payload_id": fetched.raw_payload_id,
            "sample": sample,
            "note": (
                "A successful call verifies credentials for this plan and moment; it "
                "does not verify pricing, entitlement for every competition, or licence "
                "terms."
            ),
        }
        return payload, 0
    finally:
        runtime.close()


def _sync(settings: Settings, job: str) -> tuple[dict[str, Any], int]:
    runtime = create_provider_runtime(settings)
    try:
        engine = SyncEngine(
            settings=settings,
            provider_id=runtime.provider_id,
            adapter=runtime.adapter,
        )
        summary = run_named_job(engine, job)
    finally:
        runtime.close()
    return _summary_payload(summary), 0 if summary.status is SyncStatus.SUCCESS else 1


def _sweep(settings: Settings) -> tuple[dict[str, Any], int]:
    count = mark_stale_running_runs(settings=settings)
    return {"marked_failed": count}, 0


def _migrate(settings: Settings) -> tuple[dict[str, Any], int]:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[3]
    config_path = root / "alembic.ini"
    if not config_path.exists():
        return {"error": f"alembic.ini not found at {config_path}"}, 2
    command.upgrade(Config(str(config_path)), "head")
    return {"migrated": "head", "database_url": settings.database_url}, 0


# -- helpers ---------------------------------------------------------------------


def _summary_payload(summary: SyncRunSummary) -> dict[str, Any]:
    return {
        "run_id": summary.run_id,
        "job_type": summary.job_type,
        "status": summary.status.value,
        "records_fetched": summary.counts.fetched,
        "records_created": summary.counts.created,
        "records_updated": summary.counts.updated,
        "records_unchanged": summary.counts.unchanged,
        "records_rejected": summary.counts.rejected,
        "error_count": summary.error_count,
        "started_at": _iso(summary.started_at),
        "finished_at": _iso(summary.finished_at),
        "failure": summary.failure,
    }


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)

    try:
        init_engine(settings)
        if args.command == "status":
            payload, code = _status(settings)
        elif args.command == "check-provider":
            payload, code = _check_provider(settings)
        elif args.command == "sweep-runs":
            payload, code = _sweep(settings)
        elif args.command == "sync":
            payload, code = _sync(settings, args.job)
        elif args.command == "migrate":
            payload, code = _migrate(settings)
        else:  # pragma: no cover - argparse enforces the choices
            payload, code = {"error": "unknown command"}, 2
    except AppError as exc:
        payload = {"error": exc.code, "message": str(exc)}
        code = 1
    except Exception as exc:  # noqa: BLE001 - CLI must exit with a clear message
        payload = {"error": type(exc).__name__, "message": str(exc)}
        code = 1

    print(json.dumps(payload, indent=2, default=str))
    return code


if __name__ == "__main__":
    sys.exit(main())
