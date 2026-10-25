# FlowState implementation plan

Audit date: 2026-10-24. Preserve the existing monorepo, PostgreSQL models,
Authlib login, and user changes in `apps/api/main.py` (permission received).
Development branch: `feat/flowstate-complete-platform`. Never merge to main
or provision/publicly expose resources without the requested approval.

Checklist (unchecked means acceptance criteria remain unmet):

- [ ] 1. Foundation: settings, health, schemas, migrations, API client, seed data
- [ ] 2. Persistent, authorized CRUD, search, filters, sorting, status history
- [ ] 3. Google OAuth, secure sessions, refresh, protected pages, real login
- [ ] 4. Gmail retrieval, pagination, incremental sync, deduplication, privacy
- [ ] 5. Classification, matching, confidence, provenance, correction precedence
- [ ] 6. Responsive dashboard, real metrics, management, sync, account settings
- [ ] 7. Redis/Celery persistent sync runs, retries, locks, recovery
- [ ] 8. Dockerfiles and complete local Compose stack
- [ ] 9. Separate development/production, migrations, backups
- [ ] 10. Simple EC2 Terraform, formatting, validation, plan
- [ ] 11. Repeatable EC2 deployment and recovery (approval before provisioning)
- [ ] 12. Nginx routing, TLS, renewal (domain/certificates required)
- [ ] 13. GitHub Actions checks, optional protected deployment
- [ ] 14. Integration, security, reliability, browser end-to-end tests
- [ ] 15. Accurate README, developer guide, diagrams, screenshots if verified
- [ ] 16. Vagrant three-VM lab and verification
- [ ] 17. Idempotent Ansible roles, secure configuration, deployment
- [ ] 18. Packer image, validation (approval before paid build)
- [ ] 19. Local Kubernetes deployments, storage, probes, verification
- [ ] 20. Separate managed AWS Terraform, private RDS/Redis, ALB, secrets
- [ ] 21. Structured logs, request IDs, metrics, private monitoring dashboards
- [ ] 22. Optional Gmail watch/PubSub/history, renewal, polling fallback

## Audit findings

Only three backend Python modules exist. Application routes use a process-local
dictionary with no authentication or ownership checks. Missing IDs return 200.
SQLAlchemy User/Application models exist but application routes do not use them.
There are no migrations, tests, Gmail integration, workers, or infrastructure.
OAuth uses Authlib state validation and signed cookies, but has a fallback
session secret and no CSRF origin validation for mutations. Tokens are not
persisted. Database configuration loads an ignored local environment file.

The frontend has a landing page and a single inline-styled dashboard. It calls
localhost:8000 directly, loads applications regardless of login, and lacks
network error recovery, responsive form layout, filters, history, and Gmail UI.
Next.js 16.2.7 / React 19.2.4 are already installed; avoid broad upgrades.

No credential files appear in the tracked file inventory. Local .env contents
were not printed. Credential presence alone does not verify OAuth or database
connectivity. Working tree initially contained only modified apps/api/main.py.

## Order of implementation

First close unauthenticated shared storage with persistent owned CRUD, migration
scaffolding, input validation, and isolated tests. Then finish session security
and frontend integration, classification and Gmail, then workers and containers.
Advanced infrastructure follows a verified core product. Record external
verification separately from mocked or static checks.
