"""Add users and private item ownership; preserve legacy rows unassigned."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("cognito_sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
    )
    # Existing public items remain intact, but are not assigned to an arbitrary new user.
    op.add_column("items", sa.Column("owner_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_items_owner", "items", "users", ["owner_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_items_owner_id", "items", ["owner_id"])


def downgrade():
    op.drop_index("ix_items_owner_id", "items")
    op.drop_constraint("fk_items_owner", "items", type_="foreignkey")
    op.drop_column("items", "owner_id")
    op.drop_table("users")
