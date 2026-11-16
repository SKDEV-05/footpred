"""Explicit API response schemas.

Schemas are deliberately separate from ORM models and provider DTOs: the HTTP contract is
a product decision, not a mirror of storage or of a vendor payload.
"""

from app.schemas.common import ErrorDetail, ErrorEnvelope, Page, UtcDatetime
from app.schemas.fixtures import (
    CompetitionRef,
    FixtureDetail,
    FixtureSummary,
    IdName,
    MatchStatisticsResponse,
    ResultOut,
    ScoreOut,
    SeasonRef,
    TeamRef,
    TeamStatisticsOut,
    TodayResponse,
)
from app.schemas.reference import (
    CompetitionDetail,
    CompetitionSummary,
    CountryOut,
    SeasonSummary,
    TeamDetail,
    TeamSummary,
)
from app.schemas.sync import (
    HealthOut,
    JobFreshness,
    SyncRunOut,
    SyncStatusOut,
)

__all__ = [
    "CompetitionDetail",
    "CompetitionRef",
    "CompetitionSummary",
    "CountryOut",
    "ErrorDetail",
    "ErrorEnvelope",
    "FixtureDetail",
    "FixtureSummary",
    "HealthOut",
    "IdName",
    "JobFreshness",
    "MatchStatisticsResponse",
    "Page",
    "ResultOut",
    "ScoreOut",
    "SeasonRef",
    "SeasonSummary",
    "SyncRunOut",
    "SyncStatusOut",
    "TeamDetail",
    "TeamRef",
    "TeamStatisticsOut",
    "TeamSummary",
    "TodayResponse",
    "UtcDatetime",
]
