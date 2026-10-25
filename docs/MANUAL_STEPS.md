# Manual prerequisites

No production resources have been provisioned or exposed.
Two feature increments are already pushed; no merge to main is authorized.

## Existing local work

Permission received to preserve and extend the initial uncommitted main.py OAuth
database-user lookup. Do not reset, stash, or discard it.

## Docker

Docker Compose CLI is installed, but `docker info` cannot reach the Windows
Docker engine pipe. Start Docker Desktop with Linux containers, wait until the
engine is running, then run `docker info`. This initial blocker was later resolved:
isolated dev/prod-shaped stacks and persistence checks passed. No user volumes
were deleted. See PROGRESS.md for the actual checks.

## Google integration

Local ignored apps/api/.env has Google and database settings present; values
have not been displayed or verified. Never paste credentials into chat.
Read-only PostgreSQL connectivity/schema inspection passed. Isolated PostgreSQL
tests pass; the original schema has not been changed. An approval question is
pending for backup, baseline registration and additive migrations. The prepared
helper is `python scripts/migrate_local.py --apply-approved`; do not run the
apply flag before approval.

TOKEN_ENCRYPTION_KEY is absent. Generate it locally with
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
and append it only to the ignored apps/api/.env as TOKEN_ENCRYPTION_KEY. Keep it
stable while encrypted credentials exist. Do not paste the generated value here.

When live OAuth/Gmail validation is ready:
1. Open https://console.cloud.google.com/ and select the OAuth client project.
2. Enable Gmail API in APIs & Services > Library.
3. In Google Auth Platform, configure branding, audience and test users.
4. Under Clients use a Web application OAuth client with development redirect
   http://localhost:8000/auth/google/callback. Register the exact production
   HTTPS callback only after a domain is selected and deployment approved.
5. Store client ID/secret, redirect URI and a random session secret only in the
   ignored local environment file. Gmail scopes and encrypted token storage must
   be implemented before requesting offline Gmail consent.
6. Confirm setup, then perform browser login and a controlled Gmail sync. Code
   tests alone cannot establish real OAuth or Gmail integration success.

## Infrastructure

Terraform is not on global PATH; a checksum-verified CLI exists in ignored
.tools/terraform and basic configuration validates. AWS credentials, region, instance selection, domain,
TLS certificates and cloud approval remain pending. Do not apply Terraform,
create paid resources, expose services, enable production auto-deploy, or merge
to main without explicit approval. Vagrant/Kubernetes/Packer/Ansible runtime
availability has not yet been established.
