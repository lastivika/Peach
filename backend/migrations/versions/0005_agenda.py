"""Store reviewed agendas and their original AI suggestions."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("meetings", sa.Column("agenda", JSONB(), nullable=True))
    op.add_column("meetings", sa.Column("ai_suggestion", JSONB(), nullable=True))


def downgrade():
    op.drop_column("meetings", "ai_suggestion")
    op.drop_column("meetings", "agenda")
