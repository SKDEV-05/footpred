"""Import every model so SQLAlchemy metadata and Alembic see the full schema."""

from app.models.core import Competition, Country, Match, MatchResult, Season, Team
from app.models.enums import (
    FINAL_STATUSES,
    CompetitionType,
    MatchDuration,
    MatchStatus,
    MatchWinner,
    SyncStatus,
)
from app.models.provenance import (
    DataProvider,
    DataSyncError,
    DataSyncRun,
    MatchChangeLog,
    ProviderCompetitionMapping,
    ProviderMatchMapping,
    ProviderSeasonMapping,
    ProviderTeamMapping,
    QuarantinedRecord,
    RawPayload,
)
from app.models.statistics import TeamMatchStatistics

__all__ = [
    "Competition",
    "CompetitionType",
    "Country",
    "DataProvider",
    "DataSyncError",
    "DataSyncRun",
    "FINAL_STATUSES",
    "Match",
    "MatchChangeLog",
    "MatchDuration",
    "MatchResult",
    "MatchStatus",
    "MatchWinner",
    "ProviderCompetitionMapping",
    "ProviderMatchMapping",
    "ProviderSeasonMapping",
    "ProviderTeamMapping",
    "QuarantinedRecord",
    "RawPayload",
    "Season",
    "SyncStatus",
    "Team",
    "TeamMatchStatistics",
]
