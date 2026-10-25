# Managed AWS architecture — no resources provisioned

Separate from the simple EC2 configuration. A reusable two-AZ network module
creates public app/ALB subnets and private data subnets. RDS PostgreSQL is private,
encrypted, Multi-AZ, backed up and deletion-protected. AWS manages the admin
password; provision a separate least-privileged application DB role after approval.
The app role deliberately cannot read the RDS admin secret. ElastiCache uses
private subnets, TLS, authentication, at-rest encryption and failover. Security
groups admit DB/cache traffic only from app compute, and app HTTP only from ALB.
There is no SSH ingress; use approved SSM access.

Compute is one EC2 in a public subnet with an outbound public IP, avoiding a paid
NAT for this stage. Its security group blocks direct inbound web/SSH traffic.
This is not fully HA compute; use a reviewed image/ASG deployment for that stage.
ALB listeners and web ingress default OFF. Turning them on requires an approved
ACM certificate/domain and explicit publication approval. The app must bind its
Nginx target to the instance-private interface on 8080 for ALB health checks;
the loopback-only production Compose defaults intentionally do not do that.

Run fmt/init/validate locally, then an authenticated plan with reviewed values.
DO NOT apply, destroy, delete protected resources or run a paid Packer build
without approval. Obtain an account-specific cost estimate before approval:
EC2/EBS/public IPv4, ALB/LCUs, Multi-AZ RDS/storage/backups, two cache nodes,
Secrets Manager and CloudWatch all have independent charge categories.

Populate the empty runtime secret separately with environment configuration,
least-privileged DB credentials, rediss broker URL (certificate verification
required), OAuth settings and encryption/signing keys. No secret values are in
user_data or AMIs. The narrowly scoped instance role can read only that runtime
secret and write its log streams. Deployment still needs a reviewed release,
secure secret retrieval, backup/migration gates and actual health verification.

IMPORTANT: the Redis auth-token argument is sensitive but is stored in Terraform
state. Use a separately approved encrypted remote backend with locking and
strict access before real planning/apply; never commit state or secret tfvars.
No app secret versions are created by Terraform. Do not assume `sensitive` means
the state is encrypted. Final snapshot names and retained disks need deliberate
approved lifecycle management; do not bypass deletion protection casually.

After init, `terraform test` runs five synthetic-provider plan scenarios without
AWS credentials/API calls. Assertions cover private encrypted/HA data services,
default closed web ingress, upstream security-group restrictions, narrowly scoped
runtime secret/log permissions, compute storage/IMDSv2 and input rejection for
missing/empty ACM ARNs or weak Redis tokens. These are configuration tests, not
authenticated account plans or proof that a certificate exists/is approved.
The public-web switch requires a syntactically valid ACM certificate ARN.


After approval, the docker-compose.managed.yml override disables embedded data
services, supplies external DB/broker URLs, binds Nginx to the approved private
interface, and sends service stdout/stderr through the Docker awslogs driver
using the instance role. It does not retrieve secrets or deploy on its own.
Use a mode-0600 --env-file with AWS_REGION, CLOUDWATCH_LOG_GROUP, RELEASE_ID,
APP_PRIVATE_IP, DATABASE_URL and REDIS_URL; apps/api/.env supplies other runtime
settings. Use sslmode=verify-full with a trusted RDS CA and rediss with certificate
verification. The base file still requires POSTGRES_PASSWORD for interpolation
although its embedded DB profile is disabled; a non-secret placeholder suffices
for that unused service. Never run `compose config` without --quiet on real env.
The simple deploy.sh targets embedded data; do not use it unchanged for managed
RDS. Approved managed deployment must take/verify a database backup, build the
reviewed release, stop writers, run the migration service, start services and
verify private ALB health before enabling the public listener. CloudWatch driver
network access and IAM are required; actual cloud delivery remains unverified.
