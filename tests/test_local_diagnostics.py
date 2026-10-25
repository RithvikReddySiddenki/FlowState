import unittest
from urllib.parse import urlencode

import httpx

from scripts.check_local_integrations import local_origin, valid_redirect


class LocalDiagnosticsTests(unittest.TestCase):
    def test_redirect_detects_provider_and_client_configuration_mismatches(self):
        callback = "http://localhost:8000/auth/google/callback"
        query = {
            "redirect_uri": callback,
            "client_id": "synthetic-client",
            "state": "synthetic-state",
        }

        def response(host="https://accounts.google.com", values=None):
            return httpx.Response(
                302,
                headers={
                    "location": host
                    + "/o/oauth2/v2/auth?"
                    + urlencode(query if values is None else values)
                },
            )

        self.assertTrue(valid_redirect(response(), callback, "synthetic-client"))
        for values in (
            {**query, "redirect_uri": "http://localhost:9000/auth/google/callback"},
            {**query, "client_id": "other-client"},
            {**query, "state": ""},
        ):
            self.assertFalse(valid_redirect(response(values=values), callback, "synthetic-client"))
        self.assertFalse(
            valid_redirect(
                response("https://accounts.google.com.attacker.example"),
                callback,
                "synthetic-client",
            )
        )
        self.assertFalse(
            valid_redirect(response("http://accounts.google.com"), callback, "synthetic-client")
        )

    def test_diagnostics_accept_only_loopback_origins_without_embedded_secrets(self):
        for value in ("http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000"):
            self.assertTrue(local_origin(value))
        for value in (
            "https://example.com",
            "http://secret@localhost:8000",
            "http://localhost:8000?token=secret",
            "http://localhost:8000/path",
        ):
            self.assertFalse(local_origin(value))
