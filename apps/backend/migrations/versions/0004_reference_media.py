"""store provider-supplied crest and emblem URLs

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("competitions") as batch_op:
        batch_op.add_column(sa.Column("emblem_url", sa.String(length=512), nullable=True))
    with op.batch_alter_table("teams") as batch_op:
        batch_op.add_column(sa.Column("crest_url", sa.String(length=512), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("teams") as batch_op:
        batch_op.drop_column("crest_url")
    with op.batch_alter_table("competitions") as batch_op:
        batch_op.drop_column("emblem_url")
