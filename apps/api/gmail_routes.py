from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.api.applications import owned
from apps.api.database import get_db
from apps.api.dependencies import current_user
from apps.api.ingestion import utc
from apps.api.models import (
    Application,
    ApplicationStatusHistory,
    AuthSession,
    GmailMessage,
    OAuthCredential,
    SyncRun,
    User,
)
from apps.api.tasks import sync_gmail
from apps.api.token_store import decrypt

router = APIRouter(tags=["gmail"])


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    application_id: int
    apply_status: bool = False


@router.patch("/gmail/review/{message_id}")
def resolve_review(
    message_id: int,
    decision: ReviewDecision,
    database: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    message = database.scalar(
        select(GmailMessage).where(GmailMessage.id == message_id, GmailMessage.user_id == user.id)
    )
    if message is None:
        raise HTTPException(404, "Message not found")
    application = owned(database, user, decision.application_id, lock=True)
    message.application_id = application.id
    message.review_required = False
    if decision.apply_status and message.detected_status:
        if application.current_status != message.detected_status:
            database.add(
                ApplicationStatusHistory(
                    application_id=application.id,
                    previous_status=application.current_status,
                    current_status=message.detected_status,
                    source="manual",
                    source_message_id=message.id,
                )
            )
            application.current_status = message.detected_status
        application.manual_status_locked = True
    database.commit()
    return message_response(message)


def run_response(run):
    return {
        key: getattr(run, key)
        for key in ["id", "status", "processed", "imported", "error", "created_at", "finished_at"]
    }


@router.get("/gmail/connection")
def connection(database: Session = Depends(get_db), user: User = Depends(current_user)):
    credential = database.get(OAuthCredential, user.id)
    latest = database.scalar(
        select(SyncRun)
        .where(SyncRun.user_id == user.id)
        .order_by(SyncRun.created_at.desc())
        .limit(1)
    )
    return {
        "connected": credential is not None,
        "last_synced_at": credential.last_synced_at if credential else None,
        "latest_run": run_response(latest) if latest else None,
    }


@router.post("/gmail/sync/start", status_code=202)
def start_sync(database: Session = Depends(get_db), user: User = Depends(current_user)):
    database.scalar(select(User).where(User.id == user.id).with_for_update())
    if database.get(OAuthCredential, user.id) is None:
        raise HTTPException(409, "Connect Gmail before syncing")
    active = database.scalar(
        select(SyncRun).where(SyncRun.user_id == user.id, SyncRun.status.in_(["queued", "running"]))
    )
    if active:
        if utc(active.created_at) > datetime.now(timezone.utc) - timedelta(minutes=45):
            return run_response(active)
        active.status = "failed"
        active.error = "Worker stopped or timed out. A new sync was requested."
        active.finished_at = datetime.now(timezone.utc)
        database.flush()
    run = SyncRun(id=str(uuid4()), user_id=user.id, status="queued")
    database.add(run)
    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        raise HTTPException(409, "A sync is already active") from None
    try:
        sync_gmail.apply_async(args=[run.id], task_id=run.id, retry=False)
    except Exception:
        run.status = "failed"
        run.error = "Queue unavailable. Please retry."
        run.finished_at = datetime.now(timezone.utc)
        database.commit()
        raise HTTPException(503, "Sync queue unavailable; please retry") from None
    return run_response(run)


@router.get("/gmail/sync/status/{run_id}")
def sync_status(
    run_id: str, database: Session = Depends(get_db), user: User = Depends(current_user)
):
    run = database.scalar(select(SyncRun).where(SyncRun.id == run_id, SyncRun.user_id == user.id))
    if run is None:
        raise HTTPException(404, "Sync not found")
    return run_response(run)


@router.get("/applications/{application_id}/messages")
def application_messages(
    application_id: int, database: Session = Depends(get_db), user: User = Depends(current_user)
):
    owned(database, user, application_id)
    return [
        message_response(row)
        for row in database.scalars(
            select(GmailMessage)
            .where(GmailMessage.user_id == user.id, GmailMessage.application_id == application_id)
            .order_by(GmailMessage.received_at.desc())
            .limit(200)
        )
    ]


def message_response(row):
    return {
        key: getattr(row, key)
        for key in [
            "id",
            "application_id",
            "subject",
            "sender",
            "snippet",
            "received_at",
            "detected_status",
            "confidence",
            "explanation",
            "review_required",
        ]
    }


@router.get("/gmail/review")
def review(database: Session = Depends(get_db), user: User = Depends(current_user)):
    return [
        message_response(row)
        for row in database.scalars(
            select(GmailMessage)
            .where(GmailMessage.user_id == user.id, GmailMessage.review_required.is_(True))
            .order_by(GmailMessage.received_at.desc())
            .limit(200)
        )
    ]


def revoke_and_clear(database, user):
    # Wait for an in-flight per-message transaction before deleting provenance.
    database.scalars(select(SyncRun).where(SyncRun.user_id == user.id).with_for_update()).all()
    credential = database.get(OAuthCredential, user.id)
    if credential:
        try:
            response = httpx.post(
                "https://oauth2.googleapis.com/revoke",
                data={"token": decrypt(credential.encrypted_refresh_token)},
                timeout=15,
            )
            # invalid_token means consent was already revoked.
            if response.status_code != 200 and not (
                response.status_code == 400 and response.json().get("error") == "invalid_token"
            ):
                raise ValueError("Revoke failed")
        except (httpx.HTTPError, ValueError):
            raise HTTPException(
                503, "Google revocation unavailable. Please retry disconnect."
            ) from None
        database.delete(credential)
    database.execute(delete(GmailMessage).where(GmailMessage.user_id == user.id))
    database.execute(delete(SyncRun).where(SyncRun.user_id == user.id))


@router.post("/gmail/disconnect")
def disconnect(database: Session = Depends(get_db), user: User = Depends(current_user)):
    revoke_and_clear(database, user)
    database.commit()
    return {
        "message": "Gmail access revoked and stored message metadata deleted. Applications retained."
    }


@router.delete("/account", status_code=204)
def delete_account(database: Session = Depends(get_db), user: User = Depends(current_user)):
    revoke_and_clear(database, user)
    ids = select(Application.id).where(Application.user_id == user.id)
    database.execute(
        delete(ApplicationStatusHistory).where(ApplicationStatusHistory.application_id.in_(ids))
    )
    database.execute(delete(Application).where(Application.user_id == user.id))
    database.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    database.delete(user)
    database.commit()
