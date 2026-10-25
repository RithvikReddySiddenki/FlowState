"""Persist sync heartbeat and bounded recovery attempts."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade():
    op.add_column(
        "sync_runs", sa.Column("recovery_count", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "sync_runs",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_sync_runs_updated_at", "sync_runs", ["updated_at"])


def downgrade():
    raise RuntimeError("Destructive downgrade requires a separately reviewed recovery plan")
