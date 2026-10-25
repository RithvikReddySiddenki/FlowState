"""Execute inside the isolated API validation container, never a real account DB.

Validates HTTP CRUD plus a real Redis/Celery failure-path delivery. Saves only a
synthetic browser session in /tmp for the separate live browser test.
"""

import base64
import hashlib
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from itsdangerous import TimestampSigner
from sqlalchemy import select

from apps.api.database import SessionLocal
from apps.api.models import AuthSession, SyncRun, User
from apps.api.tasks import sync_gmail


def main():
    secret = "synthetic-container-validation-secret-only"
    assert os.getenv("SESSION_SECRET") == secret
    assert os.getenv("FRONTEND_URL") == "http://localhost:13000"
    token = secrets.token_urlsafe(32)
    with SessionLocal() as database:
        user = database.scalar(select(User).where(User.google_id == "flowstate-synthetic-smoke"))
        if user is None:
            user = User(
                google_id="flowstate-synthetic-smoke",
                email="container-demo@example.test",
                name="Synthetic demo",
            )
            database.add(user)
            database.flush()
        database.add(
            AuthSession(
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                user_id=user.id,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        run_id = str(uuid4())
        database.add(SyncRun(id=run_id, user_id=user.id, status="queued"))
        database.commit()
    data = base64.b64encode(json.dumps({"sid": token}).encode())
    cookie = TimestampSigner(secret).sign(data).decode()
    with httpx.Client(
        base_url="http://127.0.0.1:8000",
        headers={"Origin": "http://localhost:13000"},
        cookies={"session": cookie},
    ) as client:
        assert client.get("/health/ready").status_code == 200
        assert client.get("/auth/me").status_code == 200
        response = client.post(
            "/applications", json={"company": "Synthetic Smoke Labs", "role": "Test Engineer"}
        )
        assert response.status_code == 201
        application_id = response.json()["id"]
        response = client.patch(
            f"/applications/{application_id}", json={"current_status": "Under Review"}
        )
        assert response.status_code == 200
        assert len(client.get(f"/applications/{application_id}/history").json()) == 2
        assert client.delete(f"/applications/{application_id}").status_code == 204
        print("Container HTTP health/authenticated CRUD/history: passed")
        sync_gmail.apply_async(args=[run_id], task_id=run_id, retry=False)
        for _ in range(30):
            status = client.get(f"/gmail/sync/status/{run_id}").json()
            if status["status"] == "failed":
                break
            time.sleep(1)
        assert status["status"] == "failed", "Real worker did not update durable run"
        print("Real Redis/Celery delivery and durable failure handling: passed")
    Path("/tmp/flowstate-smoke-session.json").write_text(json.dumps({"cookie": cookie}))
    print("Synthetic browser session prepared in container /tmp (not printed)")


if __name__ == "__main__":
    main()
