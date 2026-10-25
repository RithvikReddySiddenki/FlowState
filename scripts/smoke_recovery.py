"""Queue an interrupted synthetic run and verify recovery through real Celery."""

import os
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from apps.api.database import SessionLocal
from apps.api.models import SyncRun, User
from apps.api.tasks import recover_syncs

assert os.getenv("SESSION_SECRET") == "synthetic-container-validation-secret-only"
assert os.getenv("FRONTEND_URL") == "http://localhost:13000"

with SessionLocal() as database:
    user = database.scalar(select(User).where(User.google_id == "synthetic-recovery-smoke"))
    if user is None:
        user = User(google_id="synthetic-recovery-smoke", email="recovery@example.test")
        database.add(user)
        database.flush()
    run_id = str(uuid4())
    database.add(
        SyncRun(
            id=run_id,
            user_id=user.id,
            status="running",
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        )
    )
    database.commit()
recover_syncs.delay()
for _ in range(30):
    with SessionLocal() as database:
        run = database.get(SyncRun, run_id)
        if run.status == "failed" and run.recovery_count == 1:
            print("Real queued recovery of interrupted sync: passed")
            break
    time.sleep(1)
else:
    raise AssertionError("Recovery did not requeue the interrupted run")
