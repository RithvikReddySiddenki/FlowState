# Manual steps and approval checkpoints

## Completed with permission

- Original uncommitted main.py OAuth changes preserved and extended.
- Native local database backed up under ignored backups/, baseline registered,
  migrated through 0005 and metadata checked. Existing users retained.
- Development encryption key added to ignored apps/api/.env, never displayed.
- Real Google sign-in, Gmail consent, token refresh and a live worker sync passed.
  Metadata was persisted without printing email content.
- Docker engine is running. Isolated synthetic dev/prod checks passed.

Never paste keys/passwords/tokens in chat. Keep local environment files, backups,
rendered Kubernetes Secrets, Terraform state and kubeconfigs out of Git.

## Vagrant/VirtualBox

Vagrant and a VM provider are not installed/verified. To exercise the three-VM
lab, install Vagrant from https://developer.hashicorp.com/vagrant/install and a
compatible VirtualBox provider, enable hardware virtualization as needed, verify
roughly 6 GB VM RAM plus host overhead is available, and check 192.168.56.0/24
does not conflict with your network. Review infra/vagrant/README.md and run
vagrant up from that directory. Confirm VM health before claiming provisioning
or Ansible idempotence. Do not destroy VMs with valuable data without approval.

## AWS

No cloud resources have been provisioned, planned against your account or deleted.
Install AWS CLI if needed; prefer IAM Identity Center / `aws configure sso` and
`aws sso login` over long-lived keys. Choose the account, role and region locally.
Never send credentials in chat. Confirm identity locally using
`aws sts get-caller-identity` without publishing output.

Review Terraform, input values, state storage, cost categories and an authenticated
plan. Obtain explicit approval before apply, Packer builds, destroy, resource
deletion or paid services. No production automatic deployment or main merge is
enabled/authorized.

## Domain and HTTPS

Choose whether to use an existing domain before publication. Do not purchase or
change DNS without approval. After selecting a domain, prepare HTTPS FRONTEND_URL
and Google callback ending /api/auth/google/callback, obtain a certificate, test
Nginx and renewal, then approve publication. The TLS template is not proof of a
certificate or working public HTTPS.

## Optional Gmail push and verification

Watch/history, authenticated notification handling and renewal are implemented
and tested with synthetic fixtures. Creating a Pub/Sub topic/subscription and
verifying live public delivery require separate setup/approval; follow
GMAIL_PUSH.md. Google restricted-scope production verification remains pending;
GOOGLE_VERIFICATION.md contains owner-review drafts. Polling remains supported.

## Existing manual Docker services

User-created flowstate-redis and flowstate-postgres containers advertise 6379/5432
on all host interfaces. They were left unchanged. Restrict to loopback or use the
private Compose network before treating that setup as hardened. Preserve volumes
and settings during deliberate changes. Native development uses existing Redis;
the unused duplicate broker attempt was removed without deleting volumes or
changing those user services.


## Selected next step: AWS SSO

The owner selected AWS SSO/account-specific Terraform planning after fresh OAuth
and Gmail checks passed. AWS CLI/profile were absent at this checkpoint. Install
[AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html),
then run `aws configure sso --profile flowstate-dev` and
`aws sso login --profile flowstate-dev` using the actual IAM Identity Center portal
values/account/role. See the [SSO guide](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html).
Share only the resulting profile name and intended deployment region. Never
paste credentials or browser/device codes. Planning can resume after identity,
inputs and state protection are verified; applying still requires explicit plan
and cost approval. No cloud resources were created by integration verification.


## AWS browser-login verification (2026-10-25)

AWS CLI2.38.5 browser login now works with flowstate-dev in us-east-2. STS verified
the IAM user flowstate-developer, not root. This is aws login authentication,
not an IAM Identity Center SSO profile; no SSO portal setup is required for this
working profile. Do not overwrite it or create access keys. Both Terraform
configurations initialized/validated and real account-specific read-only plans
succeeded. See AWS_PLAN_REVIEW.md for costs, exact proposed resources and gates.
View-only permissions are sufficient for these plans, but not deployment/session
administration. No IAM changes were made; an administrator must review any
additional role/permissions after the owner selects and approves a plan.
