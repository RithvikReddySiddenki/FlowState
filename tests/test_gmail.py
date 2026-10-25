import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from cryptography.fernet import Fernet
from sqlalchemy import select

from apps.api.gmail_client import GmailClient, GmailFailure
from apps.api.ingestion import ingest
from apps.api.models import (
    Application,
    ApplicationStatusHistory,
    GmailMessage,
    OAuthCredential,
    SyncRun,
)
from apps.api.tasks import recover_syncs, sync_gmail
from apps.api.token_store import decrypt, encrypt
from tests.test_applications import ApiFixture


def message(identifier="m1", snippet="Thank you for applying", day=1, role="Engineer"):
    return {
        "id": identifier,
        "threadId": f"thread-{role}",
        "internalDate": str(int(datetime(2026, 10, day, tzinfo=timezone.utc).timestamp() * 1000)),
        "snippet": snippet,
        "payload": {
            "headers": [
                {"name": "Subject", "value": f"Application for {role} at Example Labs"},
                {"name": "From", "value": "ats@example.test"},
            ]
        },
    }


class GmailTests(ApiFixture):
    def setUp(self):
        super().setUp()
        self.env = patch.dict(os.environ, {"TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode()})
        self.env.start()
        self.addCleanup(self.env.stop)

    def credential(self):
        with self.sessions() as database:
            database.add(
                OAuthCredential(
                    user_id=1,
                    encrypted_refresh_token=encrypt("synthetic-refresh"),
                    scope="gmail.readonly",
                )
            )
            database.commit()

    def test_encrypted_roundtrip(self):
        value = encrypt("synthetic-refresh")
        self.assertNotIn("synthetic-refresh", value)
        self.assertEqual(decrypt(value), "synthetic-refresh")

    def test_duplicates_and_event_order(self):
        with self.sessions() as database:
            self.assertTrue(
                ingest(database, 1, message("new", "Interview scheduled with the team", 5))
            )
            self.assertFalse(ingest(database, 1, message("new")))
            self.assertTrue(ingest(database, 1, message("old", "We are not moving forward", 2)))
            database.commit()
            application = database.scalar(select(Application))
            self.assertEqual(application.current_status, "Interview Scheduled")
            history = database.scalars(select(ApplicationStatusHistory)).all()
            self.assertEqual(len(history), 1)
            self.assertIsNotNone(history[0].source_message_id)

    def test_manual_correction_survives_newer_email(self):
        item = self.create()
        self.client.patch(f"/applications/{item['id']}", json={"current_status": "Offer"})
        with self.sessions() as database:
            ingest(database, 1, message("late", "We are not moving forward", 10))
            database.commit()
            application = database.get(Application, item["id"])
            self.assertEqual(application.current_status, "Offer")
            self.assertTrue(database.scalar(select(GmailMessage)).review_required)

    def test_multiple_roles_and_owner_scoped_ids(self):
        with self.sessions() as database:
            ingest(database, 1, message(role="Engineer"))
            ingest(database, 1, message("m2", role="Designer"))
            ingest(database, 2, message(role="Engineer"))
            database.commit()
            self.assertEqual(len(database.scalars(select(Application)).all()), 3)
            self.assertEqual(len(database.scalars(select(GmailMessage)).all()), 3)

    def test_corrected_identity_in_same_thread_does_not_create_duplicate(self):
        with self.sessions() as database:
            ingest(database, 1, message())
            database.commit()
            application_id = database.scalar(select(Application.id))
        self.client.patch(f"/applications/{application_id}", json={"role": "Corrected role"})
        with self.sessions() as database:
            ingest(database, 1, message("next", "Interview scheduled with team", 10))
            database.commit()
            self.assertEqual(len(database.scalars(select(Application)).all()), 1)
            row = database.scalar(select(GmailMessage).where(GmailMessage.gmail_id == "next"))
            self.assertTrue(row.review_required)
            self.assertIsNone(row.application_id)

    def test_unknown_identity_requires_review_without_creating_application(self):
        row = message()
        row["payload"]["headers"][0]["value"] = "Your application"
        with self.sessions() as database:
            self.assertTrue(ingest(database, 1, row))
            database.commit()
            self.assertEqual(database.scalars(select(Application)).all(), [])
            self.assertTrue(database.scalar(select(GmailMessage)).review_required)

    def test_malformed_and_bulk_mail_skipped(self):
        with self.sessions() as database:
            self.assertFalse(ingest(database, 1, {"id": "broken"}))
            self.assertFalse(
                ingest(database, 1, message(snippet="Weekly digest: thank you for applying"))
            )

    def test_sync_requires_connection(self):
        self.assertEqual(self.client.post("/gmail/sync/start").status_code, 409)

    def test_duplicate_sync_and_status_ownership(self):
        self.credential()
        with patch("apps.api.gmail_routes.sync_gmail.apply_async") as enqueue:
            first = self.client.post("/gmail/sync/start")
            second = self.client.post("/gmail/sync/start")
            self.assertEqual(first.status_code, 202)
            self.assertEqual(first.json()["id"], second.json()["id"])
            enqueue.assert_called_once()
        self.sign_in(2)
        self.assertEqual(
            self.client.get(f"/gmail/sync/status/{first.json()['id']}").status_code, 404
        )

    def test_queue_failure_is_persistent_and_retryable(self):
        self.credential()
        with patch("apps.api.gmail_routes.sync_gmail.apply_async", side_effect=ConnectionError):
            self.assertEqual(self.client.post("/gmail/sync/start").status_code, 503)
        latest = self.client.get("/gmail/connection").json()["latest_run"]
        self.assertEqual(latest["status"], "failed")
        self.assertNotIn("ConnectionError", latest["error"])

    def test_worker_import_and_duplicate_delivery(self):
        self.credential()
        with self.sessions() as database:
            database.add(SyncRun(id="synthetic-run", user_id=1, status="queued"))
            database.commit()
        fake = MagicMock()
        fake.messages.return_value = [message(), message()]
        with (
            patch("apps.api.tasks.SessionLocal", self.sessions),
            patch("apps.api.tasks.GmailClient", return_value=fake),
        ):
            sync_gmail.run("synthetic-run")
            sync_gmail.run("synthetic-run")
        with self.sessions() as database:
            run = database.get(SyncRun, "synthetic-run")
            self.assertEqual(run.status, "completed")
            self.assertEqual(run.imported, 1)
            self.assertIsNotNone(database.get(OAuthCredential, 1).last_synced_at)
        fake.close.assert_called_once()

    def test_worker_permanent_auth_failure(self):
        self.credential()
        with self.sessions() as database:
            database.add(SyncRun(id="bad-run", user_id=1, status="queued"))
            database.commit()
        with (
            patch("apps.api.tasks.SessionLocal", self.sessions),
            patch("apps.api.tasks.GmailClient", side_effect=GmailFailure()),
        ):
            sync_gmail.run("bad-run")
        with self.sessions() as database:
            self.assertEqual(database.get(SyncRun, "bad-run").status, "failed")

    def test_worker_transient_failure_requeues_with_backoff(self):
        from celery.exceptions import Retry

        self.credential()
        with self.sessions() as database:
            database.add(SyncRun(id="retry-run", user_id=1, status="queued"))
            database.commit()
        with (
            patch("apps.api.tasks.SessionLocal", self.sessions),
            patch("apps.api.tasks.GmailClient", side_effect=GmailFailure(True)),
            patch.object(sync_gmail, "retry", side_effect=Retry) as retry,
        ):
            with self.assertRaises(Retry):
                sync_gmail.run("retry-run")
            self.assertEqual(retry.call_args.kwargs["countdown"], 30)
        with self.sessions() as database:
            self.assertEqual(database.get(SyncRun, "retry-run").status, "queued")

    def test_interrupted_sync_is_recovered_and_bounded(self):
        from datetime import timedelta

        old = datetime.now(timezone.utc) - timedelta(minutes=20)
        with self.sessions() as database:
            database.add(SyncRun(id="interrupted", user_id=1, status="running", updated_at=old))
            database.commit()
        with (
            patch("apps.api.tasks.SessionLocal", self.sessions),
            patch.object(sync_gmail, "apply_async") as enqueue,
        ):
            recover_syncs.run()
            enqueue.assert_called_once()
            with self.sessions() as database:
                run = database.get(SyncRun, "interrupted")
                self.assertEqual(run.status, "queued")
                self.assertEqual(run.recovery_count, 1)
                run.updated_at = old
                run.recovery_count = 3
                database.commit()
            recover_syncs.run()
        with self.sessions() as database:
            self.assertEqual(database.get(SyncRun, "interrupted").status, "failed")

    def test_oauth_callback_creates_revocable_session_without_leaking_token(self):
        from apps.api.main import oauth

        token = {
            "userinfo": {
                "sub": "synthetic-one",
                "email": "one@example.test",
                "email_verified": True,
            }
        }
        with (
            patch.object(oauth.google, "authorize_access_token", AsyncMock(return_value=token)),
            patch("apps.api.main.SessionLocal", self.sessions),
        ):
            response = self.client.get("/auth/google/callback", follow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(self.client.get("/auth/me").status_code, 200)
        self.assertNotIn("synthetic-one", response.headers.get("set-cookie", ""))

    def test_oauth_unverified_email_rejected(self):
        from apps.api.main import oauth

        token = {
            "userinfo": {
                "sub": "synthetic-one",
                "email": "one@example.test",
                "email_verified": False,
            }
        }
        with patch.object(oauth.google, "authorize_access_token", AsyncMock(return_value=token)):
            self.assertEqual(self.client.get("/auth/google/callback").status_code, 400)

    def test_oauth_missing_state_rejected(self):
        # Authlib validates state before exchanging codes; no real Google calls.
        self.assertEqual(self.client.get("/auth/google/callback?code=synthetic").status_code, 400)

    def test_review_association_checks_both_owners(self):
        item = self.create()
        with self.sessions() as database:
            ingest(database, 1, message("review", "We are not moving forward"))
            database.commit()
            source_id = database.scalar(select(GmailMessage.id))
        response = self.client.patch(
            f"/gmail/review/{source_id}", json={"application_id": item["id"], "apply_status": True}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.client.get(f"/applications/{item['id']}").json()["current_status"], "Rejected"
        )
        self.sign_in(2)
        self.assertEqual(
            self.client.patch(
                f"/gmail/review/{source_id}", json={"application_id": item["id"]}
            ).status_code,
            404,
        )

    def test_gmail_api_pagination_and_metadata_only(self):
        http = MagicMock()
        http.post.return_value = httpx.Response(200, json={"access_token": "synthetic"})
        http.get.side_effect = [
            httpx.Response(200, json={"messages": [{"id": "a"}], "nextPageToken": "page2"}),
            httpx.Response(200, json=message("a")),
            httpx.Response(200, json={"messages": [{"id": "b"}]}),
            httpx.Response(200, json=message("b")),
        ]
        with patch("apps.api.gmail_client.httpx.Client", return_value=http):
            client = GmailClient(encrypt("refresh"), "client", "secret")
            rows = list(client.messages(None))
            client.close()
        self.assertEqual(len(rows), 2)
        self.assertEqual(http.get.call_args_list[1].kwargs["params"][0], ("format", "metadata"))
        self.assertEqual(http.get.call_args_list[2].kwargs["params"]["pageToken"], "page2")

    def test_disconnect_deletes_metadata_and_revokes(self):
        self.credential()
        with self.sessions() as database:
            ingest(database, 1, message())
            database.commit()
        with patch("apps.api.gmail_routes.httpx.post", return_value=httpx.Response(200)):
            self.assertEqual(self.client.post("/gmail/disconnect").status_code, 200)
        with self.sessions() as database:
            self.assertIsNone(database.get(OAuthCredential, 1))
            self.assertEqual(database.scalars(select(GmailMessage)).all(), [])
            self.assertEqual(len(database.scalars(select(Application)).all()), 1)

    def test_account_deletion_removes_only_owner(self):
        self.create()
        self.assertEqual(self.client.delete("/account").status_code, 204)
        self.assertEqual(self.client.get("/auth/me").status_code, 401)
        self.sign_in(2)
        self.assertEqual(self.client.get("/auth/me").status_code, 200)
