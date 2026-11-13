"""Ingestion: provider DTOs to canonical rows.

Writes happen only here. Repositories own reads. Nothing in this package calls the
provider directly; adapters are injected.
"""

from app.ingestion.competitions import (
    ingest_competition_detail,
    upsert_competition,
    upsert_season,
)
from app.ingestion.fixtures import FixtureUpsert, upsert_fixture
from app.ingestion.outcomes import (
    IngestionCounts,
    UpsertOutcome,
    UpsertResult,
    ensure_data_provider,
)
from app.ingestion.results import upsert_result
from app.ingestion.statistics import StatisticsUpsert, upsert_statistics
from app.ingestion.teams import upsert_team

__all__ = [
    "FixtureUpsert",
    "IngestionCounts",
    "StatisticsUpsert",
    "UpsertOutcome",
    "UpsertResult",
    "ensure_data_provider",
    "ingest_competition_detail",
    "upsert_competition",
    "upsert_fixture",
    "upsert_result",
    "upsert_season",
    "upsert_statistics",
    "upsert_team",
]
