"""model evaluation persistence table

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import app.database.base

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_evaluations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("protocol_version", sa.String(length=32), nullable=False),
        sa.Column("evaluation_version", sa.String(length=32), nullable=False),
        sa.Column("dataset_id", sa.String(length=96), nullable=True),
        sa.Column("dataset_digest", sa.String(length=64), nullable=False),
        sa.Column("provider_code", sa.String(length=64), nullable=True),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("window_from", app.database.base.UTCDateTime(), nullable=True),
        sa.Column("window_to", app.database.base.UTCDateTime(), nullable=True),
        sa.Column("generated_at", app.database.base.UTCDateTime(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.Column("created_at", app.database.base.UTCDateTime(), nullable=False),
        sa.Column("updated_at", app.database.base.UTCDateTime(), nullable=False),
        sa.CheckConstraint(
            "sample_size >= 0", name=op.f("ck_model_evaluations_sample_non_negative")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_evaluations")),
        sa.UniqueConstraint(
            "protocol_version",
            "evaluation_version",
            "dataset_digest",
            name="uq_model_evaluations_protocol_version_dataset",
        ),
    )
    with op.batch_alter_table("model_evaluations", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_model_evaluations_generated_at"), ["generated_at"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_model_evaluations_dataset_digest"),
            ["dataset_digest"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("model_evaluations", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_model_evaluations_dataset_digest"))
        batch_op.drop_index(batch_op.f("ix_model_evaluations_generated_at"))
    op.drop_table("model_evaluations")
