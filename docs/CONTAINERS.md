# Containers

Copy `.env.example` to apps/api/.env only if no local file exists. Generate
SESSION_SECRET and TOKEN_ENCRYPTION_KEY locally; never paste them in chat.
Create a separate ignored root `.env` containing POSTGRES_PASSWORD with a unique
local password (URL-safe characters). This controls a NEW Compose database,
not your existing PostgreSQL. Never point the migrate service at real data
without the review described in DATABASE.md.

Development: `docker compose -f compose.yml -f docker-compose.dev.yml up --build`.
Visit http://localhost:3000 and use localhost:8000/auth/google/callback in Google.
Check `docker compose -f compose.yml -f docker-compose.dev.yml ps` and logs.
The DB volume survives container recreation. Never use down -v on valuable data.

Production-shaped build: `docker compose -f compose.yml -f docker-compose.prod.yml config --quiet`
then `up --build -d` with the same file arguments after secure settings are ready.
This intentionally binds only loopback:8080. Configure a real HTTPS FRONTEND_URL
and GOOGLE_REDIRECT_URI ending /api/auth/google/callback. Production cookies
require HTTPS. The loopback HTTP listener is for validation/approved external
TLS termination, not a claim of usable public HTTPS. Nginx strips /api/.
Do not expose its ports until deployment and TLS are explicitly approved.

Celery uses Linux process workers; Windows development should use Docker. The
DB stores sync status; Redis is a broker, not the authoritative activity store.
Repeated start calls return an active run. Workers claim runs atomically, retry
transient provider/network errors with exponential backoff, and deduplicate
message IDs. A single Celery Beat scheduler checks interrupted runs every minute.
Runs without a heartbeat for 15 minutes are requeued, up to three recoveries,
then marked failed. Users can replace a run older than 45 minutes manually.
Initial polling searches the past year; later scans overlap the last successful
scan by one day to cover indexing delay. Full mailbox/history sync is not claimed.

Shutdown workers gracefully before upgrades. Back up PostgreSQL before schema
changes. Pin production images to reviewed digests as part of deployment release
management. Local development and production-shaped stacks have passed startup
and health checks. Nginx routing, real API CRUD, desktop/mobile browser CRUD and
database persistence across DB container recreation passed. Real Redis/Celery
processes handled both a durable failure and successful ingestion with a synthetic
Gmail adapter. Native local Google login, consent, refresh and sync also passed;
the isolated container tests use synthetic credentials. Public HTTPS is unverified.

For credential-free validation, use project flowstate-validation with compose.yml,
docker-compose.dev.yml and compose.validation.yml. Set POSTGRES_PASSWORD to a
synthetic URL-safe value in the shell. Ports are loopback 13000/18000; volumes
are isolated. Pipe scripts/smoke_stack.py into `docker compose ... exec -T api
python -`, copy its /tmp/flowstate-smoke-session.json to ignored
.tools/validation-session.json, then run frontend `npx playwright test
--config=playwright.live.config.ts`. This seeds only synthetic accounts; the
application has no test-login endpoint. For the worker success-path test, start
`docker compose ... exec -d worker python -m tests.container_worker`, then pipe
scripts/smoke_worker_success.py into the validation API's Python. The test adapter
uses a dedicated queue and shuts down its own worker; production code never
imports it. Run helpers only with the supplied isolated validation settings.
