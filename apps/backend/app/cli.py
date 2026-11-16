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
from urllib.parse import urlsplit, urlunsplit

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
        "coverage",
        help="Report stored historical coverage per competition and season.",
    ).add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format (default: json).",
    )
    subparsers.add_parser(
        "check-provider", help="Verify provider configuration with one read request."
    )
    subparsers.add_parser(
        "sweep-runs", help="Mark abandoned running sync runs as failed."
    )

    retention = subparsers.add_parser(
        "purge-retention",
        help="Delete raw payloads and sync runs older than the configured retention period.",
    )
    retention.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be deleted without deleting.",
    )

    sync = subparsers.add_parser("sync", help="Run one synchronisation job.")
    sync.add_argument(
        "job",
        choices=sorted(JOB_HANDLERS),
        help="Job type to run once.",
    )
    sync.add_argument(
        "--seasons",
        default=None,
        help="Comma-separated seasons for history job (e.g. 2025,2026).",
    )
    sync.add_argument(
        "--competitions",
        default=None,
        help="Comma-separated competition codes (e.g. PL,PD).",
    )

    subparsers.add_parser("migrate", help="Apply database migrations to head.")

    evaluate = subparsers.add_parser(
        "evaluate",
        help="Run and persist the multi-competition model evaluation.",
    )
    evaluate.add_argument(
        "--as-of",
        default=None,
        help="ISO-8601 corpus checkpoint (default: now).",
    )
    evaluate.add_argument(
        "--summary-only",
        action="store_true",
        help="Print model metrics without per-competition and timeline blocks.",
    )
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


def _coverage(settings: Settings, output_format: str) -> tuple[Any, int]:
    """Report exactly which historical results are stored and how they are evidenced."""

    from sqlalchemy import case, func

    from app.models.core import Competition, Match, MatchResult, Season
    from app.models.enums import MatchStatus
    from app.models.provenance import QuarantinedRecord

    with session_scope() as session:
        rows = session.execute(
            select(
                Competition.code,
                Competition.name,
                Season.label,
                func.count(Match.id).label("matches"),
                func.sum(
                    case((Match.status == MatchStatus.FINISHED, 1), else_=0)
                ).label("finished"),
                func.sum(
                    case((MatchResult.match_id.isnot(None), 1), else_=0)
                ).label("results"),
                func.sum(
                    case((Match.raw_payload_id.isnot(None), 1), else_=0)
                ).label("payload_linked"),
                func.min(
                    case(
                        (MatchResult.match_id.isnot(None), Match.kickoff_utc)
                    )
                ).label("earliest"),
                func.max(
                    case(
                        (MatchResult.match_id.isnot(None), Match.kickoff_utc)
                    )
                ).label("latest"),
            )
            .select_from(Competition)
            .outerjoin(Season, Season.competition_id == Competition.id)
            .outerjoin(
                Match,
                (Match.competition_id == Competition.id)
                & (Match.season_id == Season.id),
            )
            .outerjoin(MatchResult, MatchResult.match_id == Match.id)
            .group_by(Competition.code, Competition.name, Season.label)
            .order_by(Competition.code, Season.label)
        ).all()

        total_matches, total_results, total_payloads = session.execute(
            select(
                func.count(Match.id),
                func.sum(case((MatchResult.match_id.isnot(None), 1), else_=0)),
                func.sum(case((Match.raw_payload_id.isnot(None), 1), else_=0)),
            )
            .select_from(Match)
            .outerjoin(MatchResult, MatchResult.match_id == Match.id)
        ).one()

        quarantine = session.execute(
            select(
                QuarantinedRecord.reason_code,
                QuarantinedRecord.reason_message,
                func.count(QuarantinedRecord.id),
            )
            .where(QuarantinedRecord.entity_type == "match")
            .group_by(
                QuarantinedRecord.reason_code, QuarantinedRecord.reason_message
            )
        ).all()

    def _iso(value):
        return value.isoformat().replace("+00:00", "Z") if value else None

    exclusions: dict[str, dict[str, Any]] = {}
    for code, message, count in quarantine:
        lowered = message.lower()
        category = (
            "extra_time_or_shootout"
            if ("extra" in lowered or "shootout" in lowered or "penalt" in lowered)
            else "other_validation"
        )
        entry = exclusions.setdefault(
            category, {"category": category, "records": 0, "reasons": []}
        )
        entry["records"] += int(count)
        entry["reasons"].append({"code": code, "message": message, "count": int(count)})

    payload = {
        "generated_at": _iso(utc_now()),
        "provider": "football_data_org",
        "totals": {
            "stored_matches": int(total_matches),
            "stored_results": int(total_results or 0),
            "payload_linked_matches": int(total_payloads or 0),
            "payload_linking_complete": int(total_payloads or 0) == int(total_matches),
        },
        "competitions": [
            {
                "competition_code": row[0],
                "competition_name": row[1],
                "season": row[2],
                "stored_matches": int(row[3] or 0),
                "finished_results": int(row[5] or 0),
                "payload_linked_matches": int(row[6] or 0),
                "earliest_finished": _iso(row[7]),
                "latest_finished": _iso(row[8]),
                "source_verification": (
                    "no_stored_matches"
                    if not int(row[3] or 0)
                    else "verified_from_archive"
                    if row[6] and int(row[6]) == int(row[3] or 0)
                    else "incomplete_provenance"
                ),
            }
            for row in rows
        ],
        "exclusions": sorted(exclusions.values(), key=lambda item: item["category"]),
        "notes": [
            "Only regulation-time finished results are counted as model history.",
            "Extra-time and penalty-shootout records are excluded rather than merged.",
            "Stored matches include upcoming fixtures; finished_results is the model corpus.",
        ],
    }

    if output_format == "markdown":
        lines = [
            "# Historical Coverage Report",
            "",
            f"Generated: {payload['generated_at']}",
            f"Provider: `{payload['provider']}` (archived raw payloads)",
            "",
            "## Totals",
            "",
            f"- Stored matches: **{payload['totals']['stored_matches']}**",
            f"- Stored finished results: **{payload['totals']['stored_results']}**",
            f"- Payload-linked matches: **{payload['totals']['payload_linked_matches']}**",
            f"- Provenance complete: **{payload['totals']['payload_linking_complete']}**",
            "",
            "## Competition and season coverage",
            "",
            "| Competition | Season | Stored | Finished | Payload-linked | Earliest finished | Latest finished | Verification |",
            "| --- | --- | ---: | ---: | ---: | --- | --- | --- |",
        ]
        for row in payload["competitions"]:
            lines.append(
                f"| {row['competition_code']} | {row['season'] or '-'} | "
                f"{row['stored_matches']} | {row['finished_results']} | "
                f"{row['payload_linked_matches']} | "
                f"{row['earliest_finished'] or '-'} | {row['latest_finished'] or '-'} | "
                f"{row['source_verification']} |"
            )
        lines.extend(["", "## Excluded provider records", ""])
        if not payload["exclusions"]:
            lines.append("No excluded match records are on file.")
        for exclusion in payload["exclusions"]:
            lines.append(
                f"### {exclusion['category']} ({exclusion['records']} records)"
            )
            lines.append("")
            for reason in exclusion["reasons"]:
                lines.append(
                    f"- `{reason['code']}` × {reason['count']}: {reason['message']}"
                )
            lines.append("")
        lines.extend(["## Notes", ""])
        lines.extend(f"- {note}" for note in payload["notes"])
        return "\n".join(lines) + "\n", 0

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


def _sync(
    settings: Settings,
    job: str,
    parameters: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], int]:
    runtime = create_provider_runtime(settings)
    try:
        engine = SyncEngine(
            settings=settings,
            provider_id=runtime.provider_id,
            adapter=runtime.adapter,
        )
        summary = run_named_job(engine, job, parameters=parameters)
    finally:
        runtime.close()
    return _summary_payload(summary), 0 if summary.status in (SyncStatus.SUCCESS, SyncStatus.PARTIAL) else 1


def _sweep(settings: Settings) -> tuple[dict[str, Any], int]:
    count = mark_stale_running_runs(settings=settings)
    return {"marked_failed": count}, 0


def _purge_retention(settings: Settings, dry_run: bool) -> tuple[dict[str, Any], int]:
    from app.ingestion.retention import (
        purge_expired_raw_payloads,
        purge_expired_sync_runs,
    )
    from app.database.session import get_session_factory

    factory = get_session_factory()
    raw_days = settings.raw_payload_retention_days
    sync_days = settings.sync_run_retention_days

    if raw_days <= 0 and sync_days <= 0:
        return {
            "raw_payload_retention_days": raw_days,
            "sync_run_retention_days": sync_days,
            "message": "No retention period is configured; nothing was deleted.",
        }, 0

    if dry_run:
        return {
            "raw_payload_retention_days": raw_days,
            "sync_run_retention_days": sync_days,
            "dry_run": True,
            "message": "Dry run: no rows were deleted.",
        }, 0

    raw_result = purge_expired_raw_payloads(
        storage_root=settings.raw_storage_dir,
        session_factory=factory,
        retention_days=raw_days,
    )
    sync_result = purge_expired_sync_runs(
        session_factory=factory,
        retention_days=sync_days,
    )
    return {
        "raw_payloads_deleted": raw_result.raw_payloads_deleted,
        "raw_bytes_freed": raw_result.raw_bytes_freed,
        "integrity_failures": raw_result.integrity_failures,
        "sync_runs_deleted": sync_result.sync_runs_deleted,
        "sync_errors_deleted": sync_result.sync_errors_deleted,
        "quarantine_deleted": sync_result.quarantine_deleted,
        "change_log_deleted": sync_result.change_log_deleted,
    }, 0


def _evaluate(settings: Settings, as_of: str | None, summary_only: bool) -> tuple[Any, int]:
    from app.repositories.evaluation import evaluate_corpus

    checkpoint = _parse_checkpoint(as_of)
    with session_scope() as session:
        record = evaluate_corpus(session, checkpoint=checkpoint)
        report = record.report

    payload: dict[str, Any] = {
        "evaluation_id": record.id,
        "protocol_version": record.protocol_version,
        "evaluation_version": record.evaluation_version,
        "dataset_id": record.dataset_id,
        "dataset_digest": record.dataset_digest,
        "sample_size": record.sample_size,
        "window_from": _iso(record.window_from),
        "window_to": _iso(record.window_to),
        "generated_at": _iso(record.generated_at),
        "models": [
            {
                "key": model.get("key"),
                "model_id": model.get("model_id"),
                "model_version": model.get("model_version"),
                "sample_size": model.get("sample_size"),
                "brier_score": model.get("brier_score"),
                "log_loss": model.get("log_loss"),
                "brier_skill_score_vs_uniform": model.get("brier_skill_score_vs_uniform"),
                "expected_calibration_error": model.get("expected_calibration_error"),
            }
            for model in report.get("models", [])
        ],
        "insufficient_competitions": [
            item.get("competition_id")
            for item in report.get("insufficient_competitions", [])
        ],
    }
    if not summary_only:
        payload["comparisons"] = report.get("comparisons", [])
        payload["competitions"] = [
            {
                "competition_id": item.get("competition_id"),
                "sample_size": item.get("sample_size"),
                "status": item.get("status"),
            }
            for item in report.get("competitions", [])
        ]
    return payload, 0


def _parse_checkpoint(value: str | None) -> datetime:
    from datetime import timezone

    if not value:
        return utc_now()
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _migrate(settings: Settings) -> tuple[dict[str, Any], int]:
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[3]
    config_path = root / "alembic.ini"
    if not config_path.exists():
        return {"error": f"alembic.ini not found at {config_path}"}, 2
    config = Config(str(config_path))
    # Alembic resolves relative paths against the process working directory, but the
    # operator may run the CLI from anywhere, so anchor them to the repository root.
    config.set_main_option("script_location", str(root / "apps" / "backend" / "migrations"))
    config.set_main_option("prepend_sys_path", str(root / "apps" / "backend"))
    command.upgrade(config, "head")
    return {"migrated": "head", "database_url": _safe_database_url(settings.database_url)}, 0


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
    configure_logging(settings.log_level, stream=sys.stderr)

    try:
        init_engine(settings)
        if args.command == "status":
            payload, code = _status(settings)
        elif args.command == "coverage":
            payload, code = _coverage(settings, args.format)
        elif args.command == "check-provider":
            payload, code = _check_provider(settings)
        elif args.command == "sweep-runs":
            payload, code = _sweep(settings)
        elif args.command == "purge-retention":
            payload, code = _purge_retention(settings, args.dry_run)
        elif args.command == "sync":
            params = {}
            if getattr(args, "seasons", None):
                params["seasons"] = args.seasons
            if getattr(args, "competitions", None):
                params["competition_ids"] = args.competitions
            payload, code = _sync(settings, args.job, parameters=params or None)
        elif args.command == "migrate":
            payload, code = _migrate(settings)
        elif args.command == "evaluate":
            payload, code = _evaluate(settings, args.as_of, args.summary_only)
        else:  # pragma: no cover - argparse enforces the choices
            payload, code = {"error": "unknown command"}, 2
    except AppError as exc:
        payload = {"error": exc.code, "message": str(exc)}
        code = 1
    except Exception as exc:  # noqa: BLE001 - CLI must exit with a safe message
        payload = {"error": type(exc).__name__, "message": "Operation failed."}
        code = 1

    if isinstance(payload, str):
        print(payload, end="")
    else:
        print(json.dumps(payload, indent=2, default=str))
    return code


def _safe_database_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.username is None and parsed.password is None:
        return value
    host = parsed.hostname or ""
    if parsed.port is not None:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))


if __name__ == "__main__":
    sys.exit(main())
