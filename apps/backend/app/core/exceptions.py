"""Typed application exceptions and their HTTP mapping.

The API maps these to one error envelope. Ingestion uses the same types so a failure
cannot be silently converted into a default value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    field: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field is not None:
            payload["field"] = self.field
        return payload


class AppError(Exception):
    """Base class for errors that are safe to describe to a client."""

    code = "internal_error"
    http_status = 500

    def __init__(
        self,
        message: str,
        *,
        details: Any = None,
        code: str | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status


class NotFoundError(AppError):
    code = "not_found"
    http_status = 404


class ConfigurationError(AppError):
    code = "configuration_error"
    http_status = 500


class RecordValidationError(AppError):
    """A provider record failed validation.

    ``issues`` is retained so the quarantine record can explain exactly what failed.
    """

    code = "validation_error"
    http_status = 422

    def __init__(self, issues: list[ValidationIssue]) -> None:
        if not issues:
            raise ValueError("RecordValidationError requires at least one issue")
        self.issues = issues
        super().__init__(
            "; ".join(issue.message for issue in issues),
            details=[issue.as_dict() for issue in issues],
        )


class IdentityAmbiguityError(AppError):
    code = "identity_ambiguous"
    http_status = 409


class ProviderError(AppError):
    code = "provider_error"
    http_status = 502


class ProviderAuthenticationError(ProviderError):
    code = "provider_authentication_failed"


class ProviderRateLimitError(ProviderError):
    code = "provider_rate_limited"


class ProviderTimeoutError(ProviderError):
    code = "provider_timeout"


class ProviderResponseError(ProviderError):
    code = "provider_response_invalid"


class UnsupportedCapabilityError(ProviderError):
    code = "unsupported_capability"
    http_status = 501


class ArchiveError(AppError):
    code = "archive_error"


class SyncRunFailedError(AppError):
    code = "sync_run_failed"
    http_status = 500

    def __init__(self, run_id: int, message: str) -> None:
        self.run_id = run_id
        super().__init__(f"sync run {run_id} failed: {message}")


@dataclass
class ErrorContext:
    """Optional structured context attached to a failure, never to a response."""

    stage: str | None = None
    entity_type: str | None = None
    external_id: str | None = None
    raw_payload_id: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)
