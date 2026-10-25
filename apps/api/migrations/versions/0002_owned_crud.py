"""Add history, action reminders, timestamps, and revocable sessions."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.add_column(
        "applications",
        sa.Column("action_required", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("applications", sa.Column("deadline", sa.DateTime(timezone=True)))
    op.add_column(
        "applications",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.add_column(
        "applications",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "application_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("previous_status", sa.String(100)),
        sa.Column("current_status", sa.String(100), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_application_status_history_application_id",
        "application_status_history",
        ["application_id"],
    )
    # Legacy reminders carry no stage information. Preserve the action and set
    # an explicit conservative stage. The migration creates no fabricated email.
    op.execute(
        "UPDATE applications SET action_required = true, current_status = 'Application Received' WHERE current_status = 'Action Required'"
    )
    op.execute(
        "INSERT INTO application_status_history (application_id, previous_status, current_status, source, created_at) SELECT id, NULL, current_status, 'migration', CURRENT_TIMESTAMP FROM applications"
    )
    op.create_table(
        "auth_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])


def downgrade():
    raise RuntimeError("Destructive downgrade requires a separately reviewed recovery plan")
