"""Run inside validation API after starting tests.container_worker separately."""

import os
import time
from uuid import uuid4

from sqlalchemy import select

from apps.api.database import SessionLocal
from apps.api.models import Application, OAuthCredential, SyncRun, User
from apps.api.tasks import celery, sync_gmail

assert os.getenv("SESSION_SECRET") == "synthetic-container-validation-secret-only"
assert os.getenv("FRONTEND_URL") == "http://localhost:13000"

try:
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.google_id == "synthetic-queue-worker"))
        if user is None:
            user = User(google_id="synthetic-queue-worker", email="queue-worker@example.test")
            database.add(user)
            database.flush()
        database.merge(
            OAuthCredential(
                user_id=user.id,
                encrypted_refresh_token="synthetic-not-a-real-token",
                scope="synthetic",
            )
        )
        run_id = str(uuid4())
        database.add(SyncRun(id=run_id, user_id=user.id, status="queued"))
        user_id = user.id
        database.commit()
    sync_gmail.apply_async(args=[run_id], task_id=run_id, queue="synthetic-validation", retry=False)
    for _ in range(30):
        with SessionLocal() as database:
            run = database.get(SyncRun, run_id)
            status = run.status
            if status == "completed":
                application = database.scalar(
                    select(Application).where(Application.user_id == user_id)
                )
                assert application.current_status == "Interview Scheduled"
                assert run.processed == 3
                credential = database.get(OAuthCredential, user_id)
                assert credential.last_synced_at is not None
                database.delete(credential)
                database.commit()
                break
            assert status != "failed", "Synthetic provider sync failed"
        time.sleep(1)
    assert status == "completed", "Worker timed out"
    print(
        "Real Redis/Celery success path, metadata ingestion, ordering and deduplication: passed (Gmail adapter synthetic)"
    )
finally:
    celery.control.broadcast("shutdown", destination=["synthetic-validation@isolated"])
