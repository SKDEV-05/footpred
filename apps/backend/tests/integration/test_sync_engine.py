"""Synchronisation engine: run lifecycle, per-item commits, quarantine, failures.

The adapter is a local double. No provider call is made, and no live behaviour is
implied by these tests.
"""

from __future__ import annotations

from datetime import timedelta
from math import nan

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core.time import utc_now
from app.database.session import session_scope
from app.ingestion.outcomes import ensure_data_provider
from app.models.core import Match, Team
from app.models.enums import SyncStatus
from app.models.provenance import (
    DataSyncError,
    DataSyncRun,
    QuarantinedRecord,
    RawPayload,
)
from app.models.statistics import TeamMatchStatistics
from app.sync.engine import SyncEngine, mark_stale_running_runs
from app.sync.jobs import (
    sync_competitions,
    sync_fixtures,
    sync_statistics,
    sync_teams,
)
from tests.factories import (
    SYNTHETIC_COMPETITION,
    SYNTHETIC_HOME,
    FakeAdapter,
    make_detail,
    make_match,
    make_score,
)


def _provider() -> int:
    with session_scope() as session:
        return ensure_data_provider(
            session, code="fake_provider", name="Fake Provider"
        ).id


def _engine(database, provider_id: int, adapter) -> SyncEngine:
    return SyncEngine(
        settings=database.settings, provider_id=provider_id, adapter=adapter
    )


def _seed_finished_fixture(provider_id: int) -> int:
    from app.ingestion.fixtures import upsert_fixture

    with session_scope() as session:
        result = upsert_fixture(
            session,
            provider_id=provider_id,
            dto=make_match(
                status="FINISHED",
                score=make_score(2, 1, ht_home=1, ht_away=0, winner="HOME_TEAM"),
            ),
            sync_run_id=None,
            kickoff_window_minutes=180,
        )
        return result.match_id


def test_successful_run_records_counts_and_is_idempotent(database):
    provider_id = _provider()
    adapter = FakeAdapter(competitions=(SYNTHETIC_COMPETITION,))
    engine = _engine(database, provider_id, adapter)

    first = engine.run(job_type="competitions", handler=sync_competitions)
    assert first.status is SyncStatus.SUCCESS
    assert first.counts.fetched == 1
    assert first.counts.created == 1
    assert first.counts.rejected == 0
    assert first.finished_at is not None

    second = engine.run(job_type="competitions", handler=sync_competitions)
    assert second.status is SyncStatus.SUCCESS
    assert second.counts.fetched == 1
    assert second.counts.unchanged == 1
    assert second.counts.created == 0

    with session_scope() as session:
        assert session.scalar(select(func.count(DataSyncRun.id))) == 2
        run = session.get(DataSyncRun, first.run_id)
        assert run is not None
        assert run.parameters is not None
        assert "run_started_at" in run.parameters
        assert run.parameters["competition_ids"] == []
        assert run.parameters["raw_payload_ids"] == [1]


def test_sync_item_transactions_use_the_engine_session_factory(database):
    provider_id = _provider()
    calls = {"count": 0}
    factory = sessionmaker(bind=database.engine, autoflush=False, expire_on_commit=False)

    def owned_factory():
        calls["count"] += 1
        return factory()

    engine = SyncEngine(
        settings=database.settings,
        provider_id=provider_id,
        adapter=FakeAdapter(competitions=(SYNTHETIC_COMPETITION,)),
        session_factory=owned_factory,
    )
    summary = engine.run(job_type="competitions", handler=sync_competitions)
    assert summary.status is SyncStatus.SUCCESS
    assert calls["count"] >= 3  # start, item, finalise


def test_partial_run_quarantines_a_bad_record_and_keeps_the_good_one(database):
    provider_id = _provider()
    valid = make_match(external_id="8001", status="TIMED")
    invalid = make_match(
        external_id="8002",
        status="TIMED",
        away=SYNTHETIC_HOME,  # same team on both sides
    )
    adapter = FakeAdapter(matches=(valid, invalid))
    engine = SyncEngine(
        # One date chunk keeps the provider double from replaying the same records for
        # each part of the window; this test is about quarantine, not chunking.
        settings=database.settings.model_copy(update={"sync_lookahead_days": 0}),
        provider_id=provider_id,
        adapter=adapter,
    )

    summary = engine.run(job_type="fixtures", handler=sync_fixtures)

    assert summary.status is SyncStatus.PARTIAL
    assert summary.counts.fetched == 2
    assert summary.counts.created == 1
    assert summary.counts.rejected == 1
    assert summary.error_count == 1

    with session_scope() as session:
        assert session.scalar(select(func.count(Match.id))) == 1
        quarantine = session.execute(select(QuarantinedRecord)).scalars().one()
        assert quarantine.entity_type == "match"
        assert quarantine.external_id == "8002"
        assert quarantine.reason_code == "validation_error"
        assert quarantine.sync_run_id == summary.run_id
        error = session.execute(select(DataSyncError)).scalars().one()
        assert error.sync_run_id == summary.run_id
        assert error.external_id == "8002"
        run = session.get(DataSyncRun, summary.run_id)
        assert run is not None
        assert run.parameters is not None
        assert run.parameters["date_from"] < run.parameters["date_to"]


def test_provider_failure_fails_the_run_and_is_recorded(database):
    provider_id = _provider()
    adapter = FakeAdapter(matches=(make_match(),), fail_matches=True)
    engine = _engine(database, provider_id, adapter)

    summary = engine.run(job_type="fixtures", handler=sync_fixtures)

    assert summary.status is SyncStatus.FAILED
    assert summary.failure is not None
    assert "provider_error" in summary.failure

    with session_scope() as session:
        assert session.scalar(select(func.count(Match.id))) == 0
        error = session.execute(select(DataSyncError)).scalars().one()
        assert error.stage == "job"
        assert error.code == "provider_error"
        run = session.get(DataSyncRun, summary.run_id)
        assert run is not None
        assert run.status is SyncStatus.FAILED
        assert run.finished_at is not None
        assert run.error_summary is not None


def test_teams_job_is_registered_and_ingests_teams(database):
    from app.sync.scheduler import JOB_HANDLERS, run_named_job

    assert JOB_HANDLERS["teams"] is sync_teams
    provider_id = _provider()
    settings = database.settings.model_copy(update={"sync_competition_ids": "EL"})
    adapter = FakeAdapter(competitions=(SYNTHETIC_COMPETITION,))
    engine = SyncEngine(settings=settings, provider_id=provider_id, adapter=adapter)

    summary = run_named_job(engine, "teams")

    assert summary.status is SyncStatus.SUCCESS
    assert summary.counts.fetched == 1
    assert summary.counts.created == 1

    with session_scope() as session:
        assert session.scalar(select(func.count(Team.id))) == 1


def test_teams_job_refuses_without_competition_ids(database):
    provider_id = _provider()
    adapter = FakeAdapter(competitions=(SYNTHETIC_COMPETITION,))
    engine = _engine(database, provider_id, adapter)

    summary = engine.run(job_type="teams", handler=sync_teams)

    assert summary.status is SyncStatus.FAILED
    assert summary.failure is not None
    assert "missing_competition_ids" in summary.failure


def test_statistics_job_stores_metric_rows_and_preserves_missing(database):
    provider_id = _provider()
    match_id = _seed_finished_fixture(provider_id)
    detail = make_detail(
        make_match(external_id="8001", status="FINISHED"),
        home_metrics={"Ball Possession": 55, "Fouls": 0},
        away_metrics={"Ball Possession": 45, "Shots": 7},
    )
    adapter = FakeAdapter(
        matches=(make_match(external_id="8001", status="FINISHED"),),
        details={"8001": detail},
        raw_payload_id=None,
    )
    engine = _engine(database, provider_id, adapter)

    summary = engine.run(job_type="statistics", handler=sync_statistics)
    assert summary.status is SyncStatus.SUCCESS
    assert summary.counts.fetched == 2
    assert summary.counts.created == 4

    with session_scope() as session:
        rows = {
            (row.team_id, row.metric): row.value
            for row in session.execute(
                select(TeamMatchStatistics).where(
                    TeamMatchStatistics.match_id == match_id
                )
            ).scalars().all()
        }
        assert len(rows) == 4
        assert 0.0 in rows.values()  # a measured zero
        assert "shots_on_goal" not in {metric for _, metric in rows}


def test_statistics_job_quarantines_one_team_and_keeps_the_other(database):
    provider_id = _provider()
    match_id = _seed_finished_fixture(provider_id)
    detail = make_detail(
        make_match(external_id="8001", status="FINISHED"),
        home_metrics={"Shots": 3},
        away_metrics={"Shots": nan},
    )
    adapter = FakeAdapter(details={"8001": detail}, raw_payload_id=None)
    summary = _engine(database, provider_id, adapter).run(
        job_type="statistics", handler=sync_statistics
    )
    assert summary.status is SyncStatus.PARTIAL
    with session_scope() as session:
        rows = session.execute(
            select(TeamMatchStatistics).where(TeamMatchStatistics.match_id == match_id)
        ).scalars().all()
        assert len(rows) == 1
        assert session.scalar(select(func.count(QuarantinedRecord.id))) == 1


def test_statistics_job_quarantines_an_unmapped_team(database):
    provider_id = _provider()
    _seed_finished_fixture(provider_id)
    detail = make_detail(
        make_match(external_id="8001", status="FINISHED"),
        home_metrics={"Ball Possession": 55},
    )
    # Rewrite the team id so the payload refers to a team that has no mapping.
    from app.providers.dto import ProviderTeamStatistics

    detail = type(detail)(
        match=detail.match,
        statistics=(
            ProviderTeamStatistics(team_external_id="does-not-exist", metrics={"shots": 1}),
        ),
    )
    adapter = FakeAdapter(details={"8001": detail}, raw_payload_id=None)
    engine = _engine(database, provider_id, adapter)

    summary = engine.run(job_type="statistics", handler=sync_statistics)
    assert summary.status is SyncStatus.PARTIAL
    assert summary.counts.rejected == 1

    with session_scope() as session:
        quarantine = session.execute(select(QuarantinedRecord)).scalars().one()
        assert quarantine.entity_type == "match_statistics"
        assert quarantine.reason_code == "validation_error"


def test_stale_running_runs_are_marked_failed(database):
    with session_scope() as session:
        stale = DataSyncRun(
            provider_id=None,
            job_type="fixtures",
            status=SyncStatus.RUNNING,
            started_at=utc_now() - timedelta(minutes=10_000),
        )
        fresh = DataSyncRun(
            provider_id=None,
            job_type="fixtures",
            status=SyncStatus.RUNNING,
            started_at=utc_now(),
        )
        session.add_all([stale, fresh])

    marked = mark_stale_running_runs(settings=database.settings)
    assert marked == 1

    with session_scope() as session:
        runs = {
            run.started_at: run
            for run in session.execute(select(DataSyncRun)).scalars().all()
        }
        statuses = sorted(run.status.value for run in runs.values())
        assert statuses == ["failed", "running"]
        error = session.execute(select(DataSyncError)).scalars().one()
        assert error.code == "stale_run"
