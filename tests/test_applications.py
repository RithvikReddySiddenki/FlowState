"""Synthetic isolated database tests; never load personal Google/DB credentials."""

import base64
import json
import hashlib
import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SESSION_SECRET"] = "synthetic-test-secret-" * 3
os.environ["FRONTEND_URL"] = "http://localhost:3000"
os.environ["APP_ENV"] = "development"

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.database import Base, get_db
from apps.api.main import app
from apps.api.models import ApplicationStatusHistory, AuthSession, User


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )

        @event.listens_for(self.engine, "connect")
        def enforce_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(self.engine)
        with self.sessions() as database:
            database.add_all([
                User(id=1, google_id="synthetic-one", email="one@example.test"),
                User(id=2, google_id="synthetic-two", email="two@example.test"),
            ])
            database.commit()

        def database_dependency():
            with self.sessions() as database:
                yield database

        app.dependency_overrides[get_db] = database_dependency
        self.client = TestClient(app)
        self.client.headers["origin"] = "http://localhost:3000"
        self.sign_in(1)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()
        self.engine.dispose()

    def sign_in(self, user_id):
        token = f"synthetic-session-{user_id}"
        with self.sessions() as database:
            if database.get(User, user_id):
                database.merge(AuthSession(
                    token_hash=hashlib.sha256(token.encode()).hexdigest(),
                    user_id=user_id, expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                ))
                database.commit()
        payload = base64.b64encode(json.dumps({"sid": token}).encode())
        signed = TimestampSigner(os.environ["SESSION_SECRET"]).sign(payload).decode()
        self.client.cookies.set("session", signed, domain="testserver.local", path="/")

    def create(self, **changes):
        payload = {"company": "Example Labs", "role": "Engineer", **changes}
        response = self.client.post("/applications", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_crud_and_persistence_across_requests(self):
        item = self.create()
        url = f"/applications/{item['id']}"
        self.assertEqual(self.client.get(url).json()["company"], "Example Labs")
        changed = self.client.patch(url, json={"role": "Senior Engineer"})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.client.get(url).json()["role"], "Senior Engineer")
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)
        with self.sessions() as database:
            self.assertEqual(database.scalars(select(ApplicationStatusHistory)).all(), [])

    def test_cross_user_isolation_on_every_route(self):
        item = self.create()
        self.sign_in(2)
        url = f"/applications/{item['id']}"
        self.assertEqual(self.client.get("/applications").json(), [])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(url + "/history").status_code, 404)
        self.assertEqual(self.client.patch(url, json={"role": "Other"}).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)

    def test_anonymous_access_rejected(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/applications").status_code, 401)
        self.assertEqual(self.client.post("/applications", json={"company": "X", "role": "Y"}).status_code, 401)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)

    def test_deleted_user_session_rejected(self):
        self.sign_in(999)
        self.assertEqual(self.client.get("/applications").status_code, 401)

    def test_validation(self):
        for payload in [
            {"company": "  ", "role": "X"},
            {"company": "X", "role": "Y", "current_status": "Invented"},
            {"company": "X", "role": "Y", "user_id": 2},
            {"company": "x" * 256, "role": "Y"},
        ]:
            self.assertEqual(self.client.post("/applications", json=payload).status_code, 422)
        item = self.create()
        for payload in [{"company": None}, {"role": " "}, {"current_status": None}, {"action_required": None}]:
            self.assertEqual(self.client.patch(f"/applications/{item['id']}", json=payload).status_code, 422)

    def test_status_history_does_not_duplicate(self):
        item = self.create()
        url = f"/applications/{item['id']}"
        self.client.patch(url, json={"current_status": "Under Review"})
        self.client.patch(url, json={"current_status": "Under Review"})
        history = self.client.get(url + "/history").json()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]["previous_status"], "Application Received")
        self.assertEqual(history[1]["source"], "manual")

    def test_action_flag_preserves_stage_and_deadline_can_be_cleared(self):
        item = self.create(current_status="Interview Scheduled")
        url = f"/applications/{item['id']}"
        response = self.client.patch(url, json={"action_required": True, "deadline": "2026-11-01T12:00:00Z"})
        self.assertEqual(response.json()["current_status"], "Interview Scheduled")
        self.assertTrue(response.json()["action_required"])
        self.assertEqual(len(self.client.get(url + "/history").json()), 1)
        self.assertIsNone(self.client.patch(url, json={"deadline": None}).json()["deadline"])

    def test_search_filter_sort_and_pagination(self):
        self.create(company="Beta", current_status="Offer", action_required=True)
        self.create(company="Alpha")
        self.assertEqual(len(self.client.get("/applications?q=beta").json()), 1)
        self.assertEqual(len(self.client.get("/applications?status=Offer&action_required=true").json()), 1)
        results = self.client.get("/applications?sort=company&direction=asc&limit=1").json()
        self.assertEqual(results[0]["company"], "Alpha")
        self.assertEqual(len(self.client.get("/applications?q=%25").json()), 0)
        self.assertEqual(self.client.get("/applications?sort=user_id").status_code, 422)
        self.assertEqual(self.client.get("/applications?limit=501").status_code, 422)

    def test_csrf_origin_validation(self):
        self.client.headers["origin"] = "https://foreign.example"
        self.assertEqual(self.client.post("/auth/logout").status_code, 403)
        del self.client.headers["origin"]
        self.assertEqual(self.client.post("/auth/logout").status_code, 403)

    def test_logout_clears_session(self):
        captured = self.client.cookies.get("session")
        self.assertEqual(self.client.post("/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)
        self.client.cookies.set("session", captured, domain="testserver.local", path="/")
        self.assertEqual(self.client.get("/auth/me").status_code, 401)

    def test_health_is_public(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/health/live").json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
