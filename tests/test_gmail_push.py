import base64
import json
import os
import time
from unittest.mock import MagicMock, patch

import httpx
from cryptography.fernet import Fernet
from fastapi import HTTPException
from joserfc import jwt
from joserfc.jwk import RSAKey

from apps.api.gmail_client import GmailClient, GmailFailure
from apps.api.gmail_push import verify_push
from apps.api.models import OAuthCredential, SyncRun
from apps.api.tasks import maintain_watches, sync_gmail
from tests import test_gmail
from tests.test_applications import ApiFixture
from tests.test_gmail import message


class PushTests(ApiFixture):
    credential = test_gmail.GmailTests.credential

    # Reuse the database/credential fixture without inheriting its tests again.
    def setUp(self):
        super().setUp()
        self.push_env = patch.dict(
            os.environ,
            {
                "TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode(),
                "ENABLE_GMAIL_PUSH": "true",
                "GMAIL_PUSH_TOPIC": "projects/synthetic/topics/gmail",
                "GMAIL_PUSH_SUBSCRIPTION": "projects/synthetic/subscriptions/gmail",
                "GMAIL_PUSH_AUDIENCE": "https://flowstate.example/api/gmail/push",
                "GMAIL_PUSH_SERVICE_ACCOUNT": "push@synthetic.iam.gserviceaccount.com",
            },
        )
        self.push_env.start()
        self.addCleanup(self.push_env.stop)

    def notification(self, history="20"):
        return {
            "subscription": os.environ["GMAIL_PUSH_SUBSCRIPTION"],
            "message": {
                "messageId": "synthetic-pubsub-id",
                "data": base64.b64encode(
                    json.dumps({"emailAddress": "one@example.test", "historyId": history}).encode()
                ).decode(),
            },
        }

    def test_push_requires_authentication_without_browser_origin(self):
        self.client.headers.pop("origin")
        self.assertEqual(self.client.post("/gmail/push", json=self.notification()).status_code, 401)
        with patch.dict(os.environ, {"ENABLE_GMAIL_PUSH": "false"}):
            self.assertEqual(
                self.client.post("/gmail/push", json=self.notification()).status_code, 404
            )

    def test_duplicate_push_single_active_run_and_stale_history(self):
        self.credential()
        self.client.headers.pop("origin")
        with (
            patch("apps.api.gmail_push.verify_push"),
            patch.object(sync_gmail, "apply_async") as queue,
        ):
            for _ in range(2):
                self.assertEqual(
                    self.client.post("/gmail/push", json=self.notification()).status_code, 204
                )
            queue.assert_called_once()
            with self.sessions() as database:
                credential = database.get(OAuthCredential, 1)
                credential.history_id = "30"
                database.commit()
            self.assertEqual(
                self.client.post("/gmail/push", json=self.notification()).status_code, 204
            )
            queue.assert_called_once()
            bad = self.notification()
            bad["subscription"] = "other"
            self.assertEqual(self.client.post("/gmail/push", json=bad).status_code, 400)

    def test_real_signature_audience_expiry_and_service_identity(self):
        key = RSAKey.generate_key(2048, parameters={"kid": "synthetic"})
        now = int(time.time())
        claims = {
            "iss": "https://accounts.google.com",
            "aud": os.environ["GMAIL_PUSH_AUDIENCE"],
            "exp": now + 600,
            "iat": now,
            "email": os.environ["GMAIL_PUSH_SERVICE_ACCOUNT"],
            "email_verified": True,
        }

        def token(values):
            return "Bearer " + jwt.encode({"alg": "RS256", "kid": "synthetic"}, values, key)

        with patch("apps.api.gmail_push.signing_keys", return_value={"keys": [key.as_dict()]}):
            verify_push(token(claims))
            for change in (
                {"aud": "other"},
                {"exp": now - 120},
                {"email": "attacker@example.test"},
                {"email_verified": False},
                {"iss": "https://attacker.example"},
            ):
                with self.assertRaises(HTTPException) as error:
                    verify_push(token({**claims, **change}))
                self.assertEqual(error.exception.status_code, 401)

    def test_history_pages_deduplicate_and_expired_cursor_polls(self):
        client = object.__new__(GmailClient)
        client.get = MagicMock(
            side_effect=[
                httpx.Response(
                    200,
                    json={
                        "history": [
                            {
                                "messagesAdded": [
                                    {"message": {"id": "new"}},
                                    {"message": {"id": "known"}},
                                ]
                            }
                        ],
                        "nextPageToken": "two",
                    },
                ),
                httpx.Response(200, json=message("new")),
                httpx.Response(
                    200,
                    json={
                        "historyId": "50",
                        "history": [{"messagesAdded": [{"message": {"id": "new"}}]}],
                    },
                ),
            ]
        )
        self.assertEqual(len(list(client.history_messages("10", None, {"known"}))), 1)
        self.assertEqual(client.completed_history_id, "50")
        self.assertEqual(client.get.call_args_list[2].kwargs["params"]["pageToken"], "two")
        client.get = MagicMock(return_value=httpx.Response(404))
        client.messages = MagicMock(return_value=iter([message("fallback")]))
        self.assertEqual(len(list(client.history_messages("old", None, set()))), 1)
        self.assertIsNone(client.completed_history_id)

    def test_failed_initial_poll_does_not_commit_watch_cursor(self):
        self.credential()
        with self.sessions() as database:
            database.add(SyncRun(id="initial-watch", user_id=1, status="queued"))
            database.commit()
        provider = MagicMock()
        provider.watch.return_value = {
            "historyId": "100",
            "expiration": str((int(time.time()) + 86400) * 1000),
        }
        provider.messages.side_effect = GmailFailure(False)
        with (
            patch("apps.api.tasks.SessionLocal", self.sessions),
            patch("apps.api.tasks.GmailClient", return_value=provider),
        ):
            sync_gmail.run("initial-watch")
        with self.sessions() as database:
            self.assertIsNone(database.get(OAuthCredential, 1).history_id)
            self.assertEqual(database.get(SyncRun, "initial-watch").status, "failed")

    def test_renewal_keeps_cursor_and_watch_failure_still_queues_polling(self):
        self.credential()
        with self.sessions() as database:
            database.get(OAuthCredential, 1).history_id = "10"
            database.commit()
        provider = MagicMock(spec=GmailClient)
        provider.watch.return_value = {
            "historyId": "100",
            "expiration": str((int(time.time()) + 604800) * 1000),
        }
        with (
            patch("apps.api.tasks.SessionLocal", self.sessions),
            patch("apps.api.tasks.GmailClient", return_value=provider),
            patch.object(sync_gmail, "apply_async") as queue,
        ):
            maintain_watches.run()
            queue.assert_called_once()
        with self.sessions() as database:
            credential = database.get(OAuthCredential, 1)
            self.assertEqual(credential.history_id, "10")
            self.assertIsNotNone(credential.watch_expires_at)
            credential.watch_expires_at = None
            database.commit()
        provider.watch.side_effect = GmailFailure(False)
        with (
            patch("apps.api.tasks.SessionLocal", self.sessions),
            patch("apps.api.tasks.GmailClient", return_value=provider),
            patch("apps.api.gmail_routes.start_sync") as start,
        ):
            maintain_watches.run()
            start.assert_called_once()

    def test_successful_initial_backfill_records_watch_only_at_completion(self):
        self.credential()
        with self.sessions() as database:
            database.add(SyncRun(id="watch-success", user_id=1, status="queued"))
            database.commit()
        provider = MagicMock(spec=GmailClient)
        provider.watch.return_value = {
            "historyId": "100",
            "expiration": str((int(time.time()) + 604800) * 1000),
        }
        provider.messages.return_value = iter([message("initial")])
        with (
            patch("apps.api.tasks.SessionLocal", self.sessions),
            patch("apps.api.tasks.GmailClient", return_value=provider),
        ):
            sync_gmail.run("watch-success")
        with self.sessions() as database:
            self.assertEqual(database.get(OAuthCredential, 1).history_id, "100")
            self.assertEqual(database.get(SyncRun, "watch-success").status, "completed")
