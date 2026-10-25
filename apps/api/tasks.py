import os
from datetime import datetime, timedelta, timezone

import httpx
from celery import Celery
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from apps.api.database import SessionLocal
from apps.api.gmail_client import GmailClient, GmailFailure
from apps.api.ingestion import ingest
from apps.api.models import OAuthCredential, SyncRun

celery = Celery("flowstate", broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"))
celery.conf.update(
    task_ignore_result=True,
    task_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=540,
    task_time_limit=600,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "recover-interrupted-syncs": {"task": "flowstate.recover_syncs", "schedule": 60.0}
    },
)


class SyncStorageFailure(Exception):
    """Safe error text; never expose SQL statements or Gmail parameters."""


@celery.task(bind=True, max_retries=4, name="flowstate.gmail_sync")
def sync_gmail(self, run_id: str):
    try:
        return _sync_gmail(self, run_id)
    except SQLAlchemyError:
        raise self.retry(
            exc=SyncStorageFailure("Sync storage temporarily unavailable"),
            countdown=min(30 * 2**self.request.retries, 480),
        ) from None


def _sync_gmail(self, run_id: str):
    with SessionLocal() as database:
        # Atomic claim makes duplicate delivery harmless.
        claimed = database.execute(
            update(SyncRun)
            .where(SyncRun.id == run_id, SyncRun.status == "queued")
            .values(status="running")
        )
        database.commit()
        if not claimed.rowcount:
            return
        run = database.get(SyncRun, run_id)
        user_id = run.user_id
        started = datetime.now(timezone.utc)
        client = None
        try:
            credential = database.get(OAuthCredential, user_id)
            if credential is None:
                raise GmailFailure()
            client = GmailClient(
                credential.encrypted_refresh_token,
                os.getenv("GOOGLE_CLIENT_ID", ""),
                os.getenv("GOOGLE_CLIENT_SECRET", ""),
            )
            for message in client.messages(credential.last_synced_at):
                # A disconnect deletes the run. Never recreate deleted user data.
                database.expire_all()
                run = database.scalar(select(SyncRun).where(SyncRun.id == run_id).with_for_update())
                if run is None:
                    database.rollback()
                    return
                imported = ingest(database, user_id, message)
                run.processed += 1
                run.imported += int(imported)
                database.commit()
            database.expire_all()
            run = database.get(SyncRun, run_id)
            credential = database.get(OAuthCredential, user_id)
            if run is None or credential is None:
                return
            credential.last_synced_at = started
            run.status = "completed"
            run.error = None
            run.finished_at = datetime.now(timezone.utc)
            database.commit()
        except Exception as error:
            database.rollback()
            run = database.get(SyncRun, run_id)
            if run is None:
                return
            retryable = (
                isinstance(error, (httpx.TransportError, SQLAlchemyError))
                or isinstance(error, GmailFailure)
                and error.retryable
            )
            retry = retryable and self.request.retries < self.max_retries
            run.status = "queued" if retry else "failed"
            run.error = (
                "Temporary Gmail failure; retrying"
                if retry
                else "Sync failed. Retry or reconnect Gmail."
            )
            if not retry:
                run.finished_at = datetime.now(timezone.utc)
            database.commit()
            if retry:
                raise self.retry(
                    exc=GmailFailure(True), countdown=min(30 * 2**self.request.retries, 480)
                )
        finally:
            if client:
                client.close()


@celery.task(bind=True, max_retries=4, name="flowstate.recover_syncs")
def recover_syncs(self):
    """Recover a lost publish or killed worker; duplicate publishes are harmless."""
    try:
        with SessionLocal() as database:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
            runs = database.scalars(
                select(SyncRun)
                .where(
                    SyncRun.status.in_(["queued", "running"]),
                    SyncRun.updated_at < cutoff,
                )
                .with_for_update(skip_locked=True)
                .limit(100)
            ).all()
            enqueue = []
            for run in runs:
                if run.recovery_count >= 3:
                    run.status = "failed"
                    run.error = "Repeated worker interruption. Please retry sync."
                    run.finished_at = datetime.now(timezone.utc)
                else:
                    run.status = "queued"
                    run.recovery_count += 1
                    run.error = "Recovering interrupted sync"
                    run.updated_at = datetime.now(timezone.utc)
                    enqueue.append(run.id)
            database.commit()
        for run_id in enqueue:
            try:
                sync_gmail.apply_async(args=[run_id], task_id=run_id, retry=False)
            except Exception:
                # Leave durable queued record; the next recovery window retries.
                pass
    except SQLAlchemyError:
        raise self.retry(
            exc=SyncStorageFailure("Sync storage temporarily unavailable"),
            countdown=min(30 * 2**self.request.retries, 480),
        ) from None
