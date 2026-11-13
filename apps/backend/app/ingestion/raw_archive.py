"""Content-addressed raw payload archive.

Every provider response is written to disk **before** it is parsed, and a
``raw_payloads`` row records the observation. The archive is committed in its own short
transaction so evidence survives a later parse or batch failure: a parser bug can be
fixed and the stored bytes replayed without re-fetching.

The file path is derived from a SHA-256 digest, never from provider input, so a hostile
payload cannot influence where bytes are written.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session, sessionmaker

from app.core.exceptions import ArchiveError
from app.core.logging import is_sensitive_key
from app.database.session import get_session_factory
from app.providers.dto import RawResponse

logger = logging.getLogger(__name__)

_MAX_PATH_LENGTH = 500


class RawArchive:
    """Write raw provider bytes and their metadata row."""

    def __init__(
        self,
        *,
        provider_code: str,
        provider_id: int,
        storage_root: Path,
        session_factory: Callable[[], Session] | sessionmaker[Session] | None = None,
    ) -> None:
        if not provider_code.strip():
            raise ValueError("provider_code must not be empty")
        self._provider_code = provider_code
        self._provider_id = provider_id
        self._root = Path(storage_root).expanduser().resolve()
        self._session_factory = session_factory or get_session_factory()

    @property
    def root(self) -> Path:
        return self._root

    def store(self, response: RawResponse, *, resource_type: str) -> int:
        """Persist the body and its metadata row, returning the row id."""

        digest = hashlib.sha256(response.content).hexdigest()
        relative_path = self._relative_path(digest)
        absolute_path = (self._root / relative_path).resolve()

        if self._root not in absolute_path.parents:
            raise ArchiveError("Refusing to write outside the archive root.")

        try:
            self._write_once(absolute_path, response.content)
        except OSError as exc:
            raise ArchiveError(
                "Could not write the provider payload to the archive."
            ) from exc

        params = {
            key: value
            for key, value in response.params.items()
            if not is_sensitive_key(key)
        }

        session = self._session_factory()
        try:
            from app.models.provenance import RawPayload

            row = RawPayload(
                provider_id=self._provider_id,
                resource_type=resource_type[:64],
                request_path=_bound(response.path, _MAX_PATH_LENGTH),
                request_params=params or None,
                fetched_at=response.fetched_at,
                http_status=response.status_code,
                content_sha256=digest,
                storage_path=relative_path,
                content_type=(response.content_type or "")[:120] or None,
                byte_size=len(response.content),
            )
            session.add(row)
            session.commit()
            payload_id = row.id
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        logger.info(
            "raw provider payload archived",
            extra={
                "event": "archive.stored",
                "component": "ingestion",
                "provider": self._provider_code,
                "path": response.path,
                "status_code": response.status_code,
            },
        )
        return payload_id

    def _relative_path(self, digest: str) -> str:
        return f"{self._provider_code}/{digest[:2]}/{digest}.json"

    def _write_once(self, path: Path, content: bytes) -> None:
        if path.exists() and path.stat().st_size == len(content):
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary_name = tempfile.mkstemp(
            dir=path.parent, prefix=".tmp-", suffix=".part"
        )
        try:
            with os.fdopen(handle, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, path)
        except Exception:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
            raise


def _bound(value: str, limit: int) -> str:
    return value if len(value) <= limit else value[:limit]
