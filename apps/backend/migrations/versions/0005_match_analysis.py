"""match analysis persistence table

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-16
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
import app.database.base

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "match_analyses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("match_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("model_id", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=32), nullable=False),
        sa.Column("dataset_id", sa.String(length=64), nullable=True),
        sa.Column("dataset_digest", sa.String(length=64), nullable=True),
        sa.Column("data_classification", sa.String(length=32), nullable=False),
        sa.Column("home_team_id", sa.Integer(), nullable=False),
        sa.Column("away_team_id", sa.Integer(), nullable=False),
        sa.Column("competition_id", sa.Integer(), nullable=False),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("kickoff_utc", app.database.base.UTCDateTime(), nullable=False),
        sa.Column("analysis_as_of", app.database.base.UTCDateTime(), nullable=False),
        sa.Column("generated_at", app.database.base.UTCDateTime(), nullable=False),
        sa.Column("expected_home_goals", sa.Float(), nullable=True),
        sa.Column("expected_away_goals", sa.Float(), nullable=True),
        sa.Column("home_win_probability", sa.Float(), nullable=True),
        sa.Column("draw_probability", sa.Float(), nullable=True),
        sa.Column("away_win_probability", sa.Float(), nullable=True),
        sa.Column("btts_probability", sa.Float(), nullable=True),
        sa.Column("over_1_5_probability", sa.Float(), nullable=True),
        sa.Column("under_1_5_probability", sa.Float(), nullable=True),
        sa.Column("over_2_5_probability", sa.Float(), nullable=True),
        sa.Column("under_2_5_probability", sa.Float(), nullable=True),
        sa.Column("over_3_5_probability", sa.Float(), nullable=True),
        sa.Column("under_3_5_probability", sa.Float(), nullable=True),
        sa.Column("home_sample_size", sa.Integer(), nullable=True),
        sa.Column("away_sample_size", sa.Integer(), nullable=True),
        sa.Column("h2h_sample_size", sa.Integer(), nullable=True),
        sa.Column("scoreline_probabilities", sa.JSON(), nullable=True),
        sa.Column("features", sa.JSON(), nullable=True),
        sa.Column("limitations", sa.JSON(), nullable=True),
        sa.Column("explanation", sa.JSON(), nullable=True),
        sa.Column("evaluation_metrics", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", app.database.base.UTCDateTime(), nullable=False),
        sa.Column("updated_at", app.database.base.UTCDateTime(), nullable=False),
        sa.CheckConstraint(
            "home_win_probability IS NULL OR (home_win_probability >= 0.0 AND home_win_probability <= 1.0)",
            name=op.f("ck_match_analyses_home_win_prob_range"),
        ),
        sa.CheckConstraint(
            "draw_probability IS NULL OR (draw_probability >= 0.0 AND draw_probability <= 1.0)",
            name=op.f("ck_match_analyses_draw_prob_range"),
        ),
        sa.CheckConstraint(
            "away_win_probability IS NULL OR (away_win_probability >= 0.0 AND away_win_probability <= 1.0)",
            name=op.f("ck_match_analyses_away_win_prob_range"),
        ),
        sa.CheckConstraint(
            "expected_home_goals IS NULL OR expected_home_goals >= 0.0",
            name=op.f("ck_match_analyses_exp_home_goals_non_negative"),
        ),
        sa.CheckConstraint(
            "expected_away_goals IS NULL OR expected_away_goals >= 0.0",
            name=op.f("ck_match_analyses_exp_away_goals_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["matches.id"],
            name=op.f("fk_match_analyses_match_id_matches"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["home_team_id"],
            ["teams.id"],
            name=op.f("fk_match_analyses_home_team_id_teams"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["away_team_id"],
            ["teams.id"],
            name=op.f("fk_match_analyses_away_team_id_teams"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["competition_id"],
            ["competitions.id"],
            name=op.f("fk_match_analyses_competition_id_competitions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_analyses")),
    )
    with op.batch_alter_table("match_analyses", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_match_analyses_match_id"), ["match_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_match_analyses_status"), ["status"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_match_analyses_created_at"), ["created_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("match_analyses", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_match_analyses_created_at"))
        batch_op.drop_index(batch_op.f("ix_match_analyses_status"))
        batch_op.drop_index(batch_op.f("ix_match_analyses_match_id"))
    op.drop_table("match_analyses")
