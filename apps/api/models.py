from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    google_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    company: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(255))
    current_status: Mapped[str] = mapped_column(String(100))
    manual_status_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    action_required: Mapped[bool] = mapped_column(Boolean, default=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    previous_status: Mapped[str | None] = mapped_column(String(100))
    current_status: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(30), default="manual")
    source_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("gmail_messages.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class OAuthCredential(Base):
    __tablename__ = "oauth_credentials"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    encrypted_refresh_token: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    history_id: Mapped[str | None] = mapped_column(String(255))
    watch_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_history_id: Mapped[str | None] = mapped_column(String(255))


class GmailMessage(Base):
    __tablename__ = "gmail_messages"
    __table_args__ = (UniqueConstraint("user_id", "gmail_id", name="uq_gmail_message_owner"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    application_id: Mapped[int | None] = mapped_column(
        ForeignKey("applications.id", ondelete="SET NULL"), index=True
    )
    gmail_id: Mapped[str] = mapped_column(String(255))
    thread_id: Mapped[str] = mapped_column(String(255), index=True)
    subject: Mapped[str] = mapped_column(String(1000))
    sender: Mapped[str] = mapped_column(String(500))
    snippet: Mapped[str] = mapped_column(String(1000))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    detected_status: Mapped[str | None] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(String(500))
    review_required: Mapped[bool] = mapped_column(Boolean, default=True)


class SyncRun(Base):
    __tablename__ = "sync_runs"
    __table_args__ = (
        Index(
            "uq_sync_active_owner",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
            sqlite_where=text("status IN ('queued', 'running')"),
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    processed: Mapped[int] = mapped_column(Integer, default=0)
    imported: Mapped[int] = mapped_column(Integer, default=0)
    recovery_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True,
    )
    error: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
