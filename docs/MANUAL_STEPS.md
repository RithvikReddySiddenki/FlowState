# Manual prerequisites

No production resources have been provisioned or exposed.

## Existing local work

Permission received to preserve and extend the initial uncommitted main.py OAuth
database-user lookup. Do not reset, stash, or discard it.

## Docker

Docker Compose CLI is installed, but `docker info` cannot reach the Windows
Docker engine pipe. Start Docker Desktop with Linux containers, wait until the
engine is running, then run `docker info`. Container integration remains blocked
until that succeeds. No volumes should be deleted to troubleshoot this.

## Google integration

Local ignored apps/api/.env has Google and database settings present; values
have not been displayed or verified. Never paste credentials into chat.

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

Terraform is not on PATH. AWS credentials, region, instance selection, domain,
TLS certificates and cloud approval remain pending. Do not apply Terraform,
create paid resources, expose services, enable production auto-deploy, or merge
to main without explicit approval. Vagrant/Kubernetes/Packer/Ansible runtime
availability has not yet been established.
