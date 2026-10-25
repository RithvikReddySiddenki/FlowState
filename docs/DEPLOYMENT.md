# Deployment runbook (not yet executed)

1. Verify local core flows, CI, backups and migrations. Review the Terraform plan
   and costs. Obtain explicit approval before apply, public exposure or paid work.
2. Provision the reviewed host only after approval. Default administration uses
   SSM with approved operator permissions; SSH is a separate opt-in restricted /32.
   For Ubuntu 24.04, review then run scripts/bootstrap-ubuntu.sh --approved as
   root. The script installs Docker packages, not application secrets.
3. Select a deployment user. Clone the repository to /opt/flowstate and check out
   the exact reviewed commit. Record the hash. Do not blindly pull main.
4. Place root .env (unique POSTGRES_PASSWORD) and apps/api/.env with restrictive
   permissions using a secure out-of-band method. Keep production signing and
   encryption keys separate from development. Never pass secret values as CLI
   arguments, bake them into images or print resolved Compose configuration.
5. Review the migration from the installed revision, back up data, confirm the
   restore process, and approve the deployment. Run scripts/deploy.sh --approved.
   It builds, backs up an existing running DB, stops old writers, migrates, starts
   services and checks loopback health. All public ports remain disabled.
6. After selecting/authorizing a domain, configure DNS to the approved address.
   Obtain a certificate with an approved ACME client and a reviewed HTTP/DNS
   challenge. Do not invent a domain or publish an endpoint without approval.
7. Render infra/nginx/https.conf.template with only DOMAIN substituted, mount
   certificates and an ACME challenge directory, and validate with nginx -t.
   Configure approved 80/443 publication in Compose and security-group ingress.
   Set FRONTEND_URL=https://your-approved-domain and Google callback to
   https://your-approved-domain/api/auth/google/callback. Rebuild/restart as needed.
8. Test HTTPS, certificate chain, /api/health/ready, login, ownership, CRUD, sync
   and worker recovery. Check sanitized logs. Only then record deployment verified.
9. Schedule certificate renewal and a deploy-hook that tests Nginx config before
   reload. Run the ACME client's renewal dry-run. Renewal is not configured here.

Redeploy by selecting the next reviewed commit, repeating backup/migration review
and deployment. A code rollback must remain compatible with the installed schema;
do not automatically downgrade. Restore backups into a separate database, verify
them, stop writes and deliberately switch connectivity when recovery is approved.
Never delete Docker volumes as a deployment technique. Store backups encrypted
with a retention policy and restricted access, then perform periodic restore drills.

There is no enabled production auto-deploy or actual server/certificate yet.
GitHub Actions validates changes only. An eventual deployment workflow should
use a protected production environment, required reviewers, short-lived
credentials, least privilege and a reviewed immutable release reference.

Local template verification is available with `python -m scripts.check_local_tls`
while the synthetic flowstate-validation Compose stack is running. It verifies
the project's marker before attaching a temporary Nginx container to its network,
binds only loopback 18443/18480, generates ignored one-day localhost certificates,
and removes its own container afterward. HTTPS API/frontend routing, redirect,
metrics isolation, TLS1.2/1.3 and a validated certificate reload passed locally.
This does not verify a public trust chain, Google HTTPS callback, DNS challenge
or actual ACME renewal; those remain steps 6-9 above.
