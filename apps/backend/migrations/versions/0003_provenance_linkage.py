"""link canonical observations and changes to raw payload evidence

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-14
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("matches") as batch_op:
        batch_op.add_column(sa.Column("raw_payload_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_matches_raw_payload_id_raw_payloads",
            "raw_payloads",
            ["raw_payload_id"],
            ["id"],
            ondelete="SET NULL",
        )
    with op.batch_alter_table("match_results") as batch_op:
        batch_op.add_column(sa.Column("raw_payload_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_match_results_raw_payload_id_raw_payloads",
            "raw_payloads",
            ["raw_payload_id"],
            ["id"],
            ondelete="SET NULL",
        )
    with op.batch_alter_table("match_change_log") as batch_op:
        batch_op.add_column(sa.Column("raw_payload_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_match_change_log_raw_payload_id_raw_payloads",
            "raw_payloads",
            ["raw_payload_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("match_change_log") as batch_op:
        batch_op.drop_constraint(
            "fk_match_change_log_raw_payload_id_raw_payloads", type_="foreignkey"
        )
        batch_op.drop_column("raw_payload_id")
    with op.batch_alter_table("match_results") as batch_op:
        batch_op.drop_constraint(
            "fk_match_results_raw_payload_id_raw_payloads", type_="foreignkey"
        )
        batch_op.drop_column("raw_payload_id")
    with op.batch_alter_table("matches") as batch_op:
        batch_op.drop_constraint(
            "fk_matches_raw_payload_id_raw_payloads", type_="foreignkey"
        )
        batch_op.drop_column("raw_payload_id")
