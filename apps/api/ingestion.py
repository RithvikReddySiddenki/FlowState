"""Idempotent metadata ingestion, conservative matching, monotonic event order."""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from apps.api.classifier import classify
from apps.api.models import Application, ApplicationStatusHistory, GmailMessage


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def ingest(database: Session, user_id: int, message: dict) -> bool:
    if not isinstance(message, dict):
        return False
    gmail_id = str(message.get("id", ""))[:255]
    if not gmail_id or database.scalar(select(GmailMessage.id).where(
        GmailMessage.user_id == user_id, GmailMessage.gmail_id == gmail_id
    )):
        return False
    try:
        received = datetime.fromtimestamp(int(message["internalDate"]) / 1000, tz=timezone.utc)
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return False
    payload = message.get("payload")
    if not isinstance(payload, dict) or not isinstance(payload.get("headers", []), list):
        return False
    headers = {str(h.get("name", "")).lower(): str(h.get("value", "")) for h in payload.get("headers", []) if isinstance(h, dict)}
    subject = str(headers.get("subject", ""))[:1000]
    sender = str(headers.get("from", ""))[:500]
    snippet = str(message.get("snippet", ""))[:1000]
    thread_id = str(message.get("threadId", ""))[:255]
    candidates = database.scalars(select(Application).join(GmailMessage, GmailMessage.application_id == Application.id).where(
        Application.user_id == user_id, GmailMessage.user_id == user_id,
        GmailMessage.thread_id == thread_id,
    ).distinct()).all() if thread_id else []
    context = candidates[0] if len(candidates) == 1 else None
    result = classify(subject, sender, snippet,
        company=context.company if context else None, role=context.role if context else None)
    if result.confidence == 0:
        return False
    application = None
    events = []
    if result.company and result.role:
        matches = database.scalars(select(Application).where(
            Application.user_id == user_id,
            func.lower(Application.company) == result.company.lower(),
            func.lower(Application.role) == result.role.lower(),
        )).all()
        if len(matches) == 1:
            application = matches[0]
        elif not matches and not result.review_required:
            application = Application(user_id=user_id, company=result.company, role=result.role,
                current_status=result.status.value, manual_status_locked=False)
            database.add(application)
            database.flush()
            events.append(ApplicationStatusHistory(application_id=application.id,
                current_status=result.status.value, source="gmail", created_at=received))
    safe = application and not result.review_required
    recent = safe and (not application.last_event_at or received > utc(application.last_event_at))
    protected = application and application.manual_status_locked
    if recent:
        if not protected and result.status and application.current_status != result.status.value:
            events.append(ApplicationStatusHistory(application_id=application.id,
                previous_status=application.current_status, current_status=result.status.value,
                source="gmail", created_at=received))
            application.current_status = result.status.value
        if not protected:
            application.action_required = result.action_required
            application.deadline = result.deadline
        application.last_event_at = received
    source = GmailMessage(user_id=user_id, gmail_id=gmail_id, thread_id=thread_id,
        application_id=application.id if application else None, subject=subject, sender=sender,
        snippet=snippet, received_at=received, detected_status=result.status.value if result.status else None,
        confidence=result.confidence, explanation=result.reason,
        review_required=result.review_required or not application or bool(protected))
    database.add(source)
    database.flush()
    for event in events:
        event.source_message_id = source.id
        database.add(event)
    database.flush()
    return True
