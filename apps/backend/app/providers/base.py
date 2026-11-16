"""Provider adapter contract and capability declaration.

An adapter translates one vendor's transport and schema into internal DTOs. It is
stateless with respect to canonical data: it fetches, archives, and parses, and it never
writes to the database. A dataset the platform does not model is declared unsupported and
raises instead of returning empty or fabricated data.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import ClassVar, Mapping, Protocol

from app.core.exceptions import UnsupportedCapabilityError
from app.providers.dto import (
    Fetched,
    ProviderCompetition,
    ProviderMatch,
    ProviderMatchDetail,
    ProviderSeason,
    ProviderTeam,
    RawResponse,
)


@dataclass(frozen=True)
class ProviderCapabilities:
    competitions: bool = False
    seasons: bool = False
    teams: bool = False
    fixtures: bool = False
    results: bool = False
    match_statistics: bool = False
    lineups: bool = False
    match_events: bool = False


class RawArchiveSink(Protocol):
    def store(self, response: RawResponse, *, resource_type: str) -> int:
        """Persist a response before it is parsed and return the archive row id."""


class RateLimiter(Protocol):
    def acquire(self) -> None:
        """Block until one request is permitted."""


class ProviderHttpClientProtocol(Protocol):
    def get(
        self, path: str, *, params: Mapping[str, str] | None = None
    ) -> RawResponse:
        """Perform one authenticated GET and return the raw response."""


class ProviderAdapter(ABC):
    code: ClassVar[str]
    name: ClassVar[str]
    capabilities: ClassVar[ProviderCapabilities]

    def supports(self, capability: str) -> bool:
        return bool(getattr(self.capabilities, capability, False))

    def require(self, capability: str) -> None:
        if not self.supports(capability):
            raise UnsupportedCapabilityError(
                f"Provider '{self.code}' does not support '{capability}' "
                "in this platform."
            )

    @abstractmethod
    def fetch_competitions(self) -> Fetched[list[ProviderCompetition]]:
        """List competitions available to the authenticated client."""

    @abstractmethod
    def fetch_competition(self, external_id: str) -> Fetched[ProviderCompetition]:
        """Fetch one competition, including its seasons when documented."""

    @abstractmethod
    def fetch_seasons(self, competition_external_id: str) -> Fetched[list[ProviderSeason]]:
        """List seasons for a competition."""

    @abstractmethod
    def fetch_teams(
        self,
        competition_external_id: str,
        season_external_id: str | None = None,
    ) -> Fetched[list[ProviderTeam]]:
        """List teams participating in a competition season."""

    @abstractmethod
    def fetch_matches(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        competition_external_id: str | None = None,
        season_external_id: str | None = None,
        status: str | None = None,
    ) -> Fetched[list[ProviderMatch]]:
        """Fetch fixtures/results in a bounded date range, season, or competition."""

    @abstractmethod
    def fetch_match_detail(self, match_external_id: str) -> Fetched[ProviderMatchDetail]:
        """Fetch one match with whatever detail the provider supplies."""

    # Optional capabilities. Base implementations fail loudly rather than pretending.
    def fetch_lineups(self, match_external_id: str) -> Fetched[object]:
        raise UnsupportedCapabilityError(
            f"Provider '{self.code}' lineup ingestion is not supported in Phase 3."
        )

    def fetch_match_events(self, match_external_id: str) -> Fetched[object]:
        raise UnsupportedCapabilityError(
            f"Provider '{self.code}' event ingestion is not supported in Phase 3."
        )
