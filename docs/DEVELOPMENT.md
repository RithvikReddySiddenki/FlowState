# Developer guide

From the repository root, create/activate a Python 3.12 virtual environment and
run `python -m pip install -r requirements.txt`. Copy `.env.example` to the
ignored `apps/api/.env` and configure PostgreSQL and a random session secret.
Never overwrite an existing environment file. See DATABASE.md before migrations.
For a fresh empty database run `python -m alembic upgrade head`.

Run `python -m uvicorn apps.api.main:app --reload --no-access-log` and in apps/web run `npm ci`
then `npm run dev`. Optional apps/web/.env.local can set NEXT_PUBLIC_API_URL.
The default frontend/API addresses are localhost:3000 and localhost:8000.
Use the same hostname consistently, including the Google redirect URI.

To verify an existing local installation without printing credentials, run
`python -m scripts.check_local_integrations`. It checks ignored credential-file
loading, callback/client/state, schema, readiness and Celery. Add `--sync` to
explicitly queue a real sync for the sole connected account and wait for its
durable result; multiple accounts must use their signed-in dashboard. It never
prints Google authorization URLs, tokens, cookies, message contents or DB URLs.
The local callback is http://localhost:8000/auth/google/callback; register that
exact URI in the Google Web OAuth client. Fresh browser sign-in and separate
Gmail consent remain manual checks; the script cannot inspect Cloud Console.

If both native PostgreSQL and a Docker database are installed, confirm which
server the backend actually uses before any migration or data move. The command
reports the application's PostgreSQL major version without revealing its URL.
Do not change DATABASE_URL merely because another database container is running.

Run `python -m unittest discover -v` from root. Tests use synthetic data and a
separate in-memory SQLite database with foreign keys enabled, never your local
PostgreSQL or Gmail credentials. Run frontend `npm run lint`, `npx tsc --noEmit`
and `npm run build`. SQLite tests do not replace PostgreSQL integration tests.
Run `npm run build` before `npm run test:e2e`: browser fixture tests serve the
compiled app on loopback port 3100, so they can coexist with development on 3000.

Browser mutations require an Origin header matching FRONTEND_URL to prevent
CSRF. The disabled-by-default Pub/Sub POST instead requires a verified Google
service identity; see GMAIL_PUSH.md. Protected endpoints require a valid server-side login session. Auth/me
returns 401 when unauthenticated. API pagination defaults to 100 and maxes at
500 records per page. Treat Action Required as an independent flag; six stages
remain stable while reminders/deadlines change.

Troubleshooting: missing/short SESSION_SECRET prevents startup intentionally;
missing tables require reviewed migrations; 401 requires login; 403 requires a
trusted Origin; API/network errors appear with retry guidance. No production
deployment workflow is enabled. See MANUAL_STEPS.md for external prerequisites.
