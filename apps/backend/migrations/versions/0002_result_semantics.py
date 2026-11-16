"""preserve extra-time and shootout score components

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("match_results") as batch_op:
        batch_op.add_column(sa.Column("extra_home_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("extra_away_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("shootout_home_score", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("shootout_away_score", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "extra_time_scores_together",
            "(extra_home_score IS NULL AND extra_away_score IS NULL) OR "
            "(extra_home_score IS NOT NULL AND extra_away_score IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "shootout_scores_together",
            "(shootout_home_score IS NULL AND shootout_away_score IS NULL) OR "
            "(shootout_home_score IS NOT NULL AND shootout_away_score IS NOT NULL)",
        )
        batch_op.create_check_constraint(
            "extra_scores_non_negative",
            "(extra_home_score IS NULL OR extra_home_score >= 0) AND "
            "(extra_away_score IS NULL OR extra_away_score >= 0)",
        )
        batch_op.create_check_constraint(
            "shootout_scores_non_negative",
            "(shootout_home_score IS NULL OR shootout_home_score >= 0) AND "
            "(shootout_away_score IS NULL OR shootout_away_score >= 0)",
        )


def downgrade() -> None:
    with op.batch_alter_table("match_results") as batch_op:
        batch_op.drop_constraint("shootout_scores_non_negative", type_="check")
        batch_op.drop_constraint("extra_scores_non_negative", type_="check")
        batch_op.drop_constraint("shootout_scores_together", type_="check")
        batch_op.drop_constraint("extra_time_scores_together", type_="check")
        batch_op.drop_column("shootout_away_score")
        batch_op.drop_column("shootout_home_score")
        batch_op.drop_column("extra_away_score")
        batch_op.drop_column("extra_home_score")
