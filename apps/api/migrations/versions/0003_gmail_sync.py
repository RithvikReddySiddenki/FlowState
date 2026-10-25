"""Encrypted credentials, metadata provenance and durable sync runs."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"


def upgrade():
    op.add_column("applications", sa.Column("manual_status_locked", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("applications", sa.Column("last_event_at", sa.DateTime(timezone=True)))
    op.create_table("oauth_credentials",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
    )
    op.create_table("gmail_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id", ondelete="SET NULL")),
        sa.Column("gmail_id", sa.String(255), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(1000), nullable=False),
        sa.Column("sender", sa.String(500), nullable=False),
        sa.Column("snippet", sa.String(1000), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_status", sa.String(100)),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.String(500), nullable=False),
        sa.Column("review_required", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("user_id", "gmail_id", name="uq_gmail_message_owner"),
    )
    for column in ("user_id", "application_id", "thread_id"):
        op.create_index(f"ix_gmail_messages_{column}", "gmail_messages", [column])
    with op.batch_alter_table("application_status_history") as batch:
        batch.add_column(sa.Column("source_message_id", sa.Integer()))
        batch.create_foreign_key("fk_history_source_message", "gmail_messages", ["source_message_id"], ["id"], ondelete="SET NULL")
    op.create_table("sync_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("processed", sa.Integer(), nullable=False),
        sa.Column("imported", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_sync_runs_user_id", "sync_runs", ["user_id"])
    op.create_index("uq_sync_active_owner", "sync_runs", ["user_id"], unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
        sqlite_where=sa.text("status IN ('queued', 'running')"))


def downgrade():
    raise RuntimeError("Destructive downgrade requires a separately reviewed recovery plan")
