"""Credential-safe local diagnostics. --sync explicitly queues a real Gmail sync.

Never prints authorization URLs, cookies, tokens, email addresses or DB URLs.
Browser sign-in/Google consent still require the account owner.
"""

import argparse
import subprocess
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def valid_redirect(response, expected_uri, expected_client_id):
    destination = urlparse(response.headers.get("location", ""))
    query = parse_qs(destination.query)
    return (
        response.status_code in {302, 303, 307}
        and destination.scheme == "https"
        and destination.hostname == "accounts.google.com"
        and query.get("redirect_uri") == [expected_uri]
        and query.get("client_id") == [expected_client_id]
        and bool(query.get("state"))
    )


def local_origin(value):
    parsed = urlparse(value)
    return (
        parsed.scheme in {"http", "https"}
        and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
        and parsed.path in {"", "/"}
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--sync", action="store_true", help="Sync the sole connected Gmail account")
    parser.add_argument("--wait-seconds", type=int, default=90)
    args = parser.parse_args()
    if not local_origin(args.api_url) or not 1 <= args.wait_seconds <= 600:
        parser.error("Use a loopback API origin and a wait between 1 and 600 seconds")
    origin = args.api_url.rstrip("/")
    cfg = dotenv_values(ROOT / "apps/api/.env")
    checks = []

    def check(label, passed):
        checks.append(bool(passed))
        print(f"{'PASS' if passed else 'FAIL'}: {label}", flush=True)

    for key in (
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "SESSION_SECRET",
        "TOKEN_ENCRYPTION_KEY",
    ):
        check(f"{key} is configured (value hidden)", bool(cfg.get(key)))
    callback = f"{origin}/auth/google/callback"
    check("Configured callback matches this local API", cfg.get("GOOGLE_REDIRECT_URI") == callback)
    check(
        "Credential file is ignored by Git",
        subprocess.run(
            ["git", "check-ignore", "-q", "apps/api/.env"], cwd=ROOT, capture_output=True
        ).returncode
        == 0,
    )
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy import func, select, text

    from apps.api.database import SessionLocal
    from apps.api.main import oauth
    from apps.api.models import OAuthCredential, SyncRun, User
    from apps.api.tasks import celery

    check(
        "Backend configuration loads the credentials from the file",
        bool(cfg.get("GOOGLE_CLIENT_ID"))
        and oauth.google.client_id == cfg["GOOGLE_CLIENT_ID"]
        and oauth.google.client_secret == cfg.get("GOOGLE_CLIENT_SECRET"),
    )
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "apps/api/migrations"))
    expected_head = ScriptDirectory.from_config(config).get_current_head()
    with SessionLocal() as database:
        check(
            "Application database is at the current migration",
            database.scalar(text("SELECT version_num FROM alembic_version")) == expected_head,
        )
        major = int(database.scalar(text("SHOW server_version_num"))) // 10000
        print(f"Application PostgreSQL major version: {major}", flush=True)
        connected = database.scalar(select(func.count()).select_from(OAuthCredential))
        check("A Gmail credential is stored", connected > 0)
    check("At least one Celery worker responds", bool(celery.control.ping(timeout=4)))
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        check("API readiness", client.get(f"{origin}/health/ready").status_code == 200)
        response = client.get(f"{origin}/auth/google/login")
        check(
            "Live Google redirect, client identity and OAuth state",
            valid_redirect(response, callback, cfg.get("GOOGLE_CLIENT_ID")),
        )
    if not all(checks):
        print("Resolve failed checks before requesting another sync.")
        return 1
    if args.sync:
        from apps.api.gmail_routes import start_sync

        with SessionLocal() as database:
            owners = list(database.scalars(select(OAuthCredential.user_id)))
            if len(owners) != 1:
                print("Use the signed-in dashboard to select your account; no sync requested.")
                return 1
            run_id = start_sync(database, database.get(User, owners[0]))["id"]
        deadline = time.monotonic() + args.wait_seconds
        while time.monotonic() < deadline:
            with SessionLocal() as database:
                run = database.get(SyncRun, run_id)
                if run is None:
                    print("Sync was removed; check connection status in the dashboard.")
                    return 1
                if run.status in {"completed", "failed"}:
                    check("Real Gmail synchronization completed", run.status == "completed")
                    return 0 if all(checks) else 1
            time.sleep(1)
        print("Sync remains active. Check progress in the dashboard; no failure assumed.")
        return 2
    print(
        "Read-only checks passed. Complete sign-in/consent in the browser to verify Google's registered callback."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # Driver/provider exception text can contain credentials or SQL parameters.
        print(
            f"Check stopped safely: {type(error).__name__}. Inspect local setup; no private error data printed."
        )
        raise SystemExit(1) from None
