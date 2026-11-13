"""Wire a provider adapter to its archive and HTTP client.

This is the only place that combines settings, persistence, and a vendor adapter, which
keeps the provider package free of ORM imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import httpx
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.database.session import get_session_factory, session_scope
from app.ingestion.outcomes import ensure_data_provider
from app.ingestion.raw_archive import RawArchive
from app.providers.adapters.football_data_org import FootballDataOrgAdapter
from app.providers.base import ProviderAdapter
from app.providers.http import ProviderHttpClient, build_http_client

FOOTBALL_DATA_ORG_CODE = "football_data_org"
FOOTBALL_DATA_ORG_NAME = "football-data.org"


@dataclass
class ProviderRuntime:
    provider_id: int
    adapter: ProviderAdapter
    http: ProviderHttpClient | None = None

    def close(self) -> None:
        if self.http is not None:
            self.http.close()


def create_provider_runtime(
    settings: Settings,
    *,
    session_factory: sessionmaker[Session] | Callable[[], Session] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> ProviderRuntime:
    """Create the configured provider. Raises if no token is configured."""

    factory = session_factory or get_session_factory()
    with session_scope() as session:
        provider = ensure_data_provider(
            session,
            code=FOOTBALL_DATA_ORG_CODE,
            name=FOOTBALL_DATA_ORG_NAME,
            base_url=settings.football_data_org_base_url,
        )
        provider_id = provider.id

    http = build_http_client(settings, transport=transport)
    archive = RawArchive(
        provider_code=FOOTBALL_DATA_ORG_CODE,
        provider_id=provider_id,
        storage_root=settings.raw_storage_dir,
        session_factory=factory,
    )
    adapter = FootballDataOrgAdapter(http=http, archive=archive)
    return ProviderRuntime(provider_id=provider_id, adapter=adapter, http=http)
