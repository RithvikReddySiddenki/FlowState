"""Optional Gmail history cursor and watch lifecycle."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade():
    for name in ("history_id", "notified_history_id"):
        op.add_column("oauth_credentials", sa.Column(name, sa.String(255), nullable=True))
    op.add_column(
        "oauth_credentials",
        sa.Column("watch_expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    raise RuntimeError("Destructive downgrade requires a separately reviewed recovery plan")
