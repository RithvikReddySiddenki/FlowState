"""Baseline matching the original SQLAlchemy tables.

Existing databases must be inspected before stamping 0001. Never auto-stamp.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("google_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
    )
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("role", sa.String(255), nullable=False),
        sa.Column("current_status", sa.String(100), nullable=False),
    )
    op.create_index("ix_applications_user_id", "applications", ["user_id"])


def downgrade():
    raise RuntimeError("Destructive downgrade requires a separately reviewed recovery plan")
