"""Provider identity, raw evidence, synchronisation history, and quarantine."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UTCDateTime
from app.models.enums import SyncStatus, enum_column


class DataProvider(TimestampMixin, Base):
    __tablename__ = "data_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    base_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )


class ProviderCompetitionMapping(TimestampMixin, Base):
    __tablename__ = "provider_competition_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider_id", "external_id", name="uq_provider_competition_external"
        ),
        UniqueConstraint(
            "provider_id", "competition_id", name="uq_provider_competition_internal"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="confidence_range"
        ),
        Index("ix_provider_competition_mappings_competition_id", "competition_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("data_providers.id", ondelete="RESTRICT"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ProviderSeasonMapping(TimestampMixin, Base):
    __tablename__ = "provider_season_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider_id", "external_id", name="uq_provider_season_external"
        ),
        UniqueConstraint(
            "provider_id", "season_id", name="uq_provider_season_internal"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="confidence_range"
        ),
        Index("ix_provider_season_mappings_season_id", "season_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("data_providers.id", ondelete="RESTRICT"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="RESTRICT"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ProviderTeamMapping(TimestampMixin, Base):
    __tablename__ = "provider_team_mappings"
    __table_args__ = (
        UniqueConstraint("provider_id", "external_id", name="uq_provider_team_external"),
        UniqueConstraint("provider_id", "team_id", name="uq_provider_team_internal"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="confidence_range"
        ),
        Index("ix_provider_team_mappings_team_id", "team_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("data_providers.id", ondelete="RESTRICT"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class ProviderMatchMapping(TimestampMixin, Base):
    __tablename__ = "provider_match_mappings"
    __table_args__ = (
        UniqueConstraint(
            "provider_id", "external_id", name="uq_provider_match_external"
        ),
        UniqueConstraint("provider_id", "match_id", name="uq_provider_match_internal"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="confidence_range"
        ),
        Index("ix_provider_match_mappings_match_id", "match_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("data_providers.id", ondelete="RESTRICT"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class RawPayload(Base):
    __tablename__ = "raw_payloads"
    __table_args__ = (
        CheckConstraint("byte_size >= 0", name="byte_size_non_negative"),
        Index("ix_raw_payloads_content_sha256", "content_sha256"),
        Index("ix_raw_payloads_fetched_at", "fetched_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("data_providers.id", ondelete="RESTRICT"), nullable=False
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    request_path: Mapped[str] = mapped_column(String(500), nullable=False)
    request_params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)


class DataSyncRun(Base):
    __tablename__ = "data_sync_runs"
    __table_args__ = (
        Index("ix_data_sync_runs_started_at", "started_at"),
        Index("ix_data_sync_runs_job_type_started_at", "job_type", "started_at"),
        Index("ix_data_sync_runs_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_providers.id", ondelete="RESTRICT"), nullable=True
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(
        enum_column(SyncStatus, name="sync_status"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    records_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_unchanged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    errors: Mapped[list["DataSyncError"]] = relationship(
        back_populates="sync_run", viewonly=True
    )


class DataSyncError(Base):
    __tablename__ = "data_sync_errors"
    __table_args__ = (
        Index("ix_data_sync_errors_sync_run_id", "sync_run_id"),
        Index("ix_data_sync_errors_code", "code"),
        Index("ix_data_sync_errors_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sync_run_id: Mapped[int] = mapped_column(
        ForeignKey("data_sync_runs.id", ondelete="RESTRICT"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_payload_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_payloads.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    sync_run: Mapped[DataSyncRun] = relationship(
        back_populates="errors", viewonly=True
    )


class QuarantinedRecord(Base):
    __tablename__ = "quarantined_records"
    __table_args__ = (
        Index("ix_quarantined_records_created_at", "created_at"),
        Index("ix_quarantined_records_entity", "entity_type", "external_id"),
        Index("ix_quarantined_records_resolved_at", "resolved_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("data_providers.id", ondelete="RESTRICT"), nullable=False
    )
    sync_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sync_runs.id", ondelete="SET NULL"), nullable=True
    )
    raw_payload_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_payloads.id", ondelete="SET NULL"), nullable=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_message: Mapped[str] = mapped_column(String(2000), nullable=False)
    payload_excerpt: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class MatchChangeLog(Base):
    __tablename__ = "match_change_log"
    __table_args__ = (
        Index("ix_match_change_log_match_id_created_at", "match_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False
    )
    sync_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sync_runs.id", ondelete="SET NULL"), nullable=True
    )
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_fields: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    previous_values: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    new_values: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    provider_last_updated: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
