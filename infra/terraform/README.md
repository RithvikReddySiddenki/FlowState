# Initial EC2 deployment

Default administration uses SSM with no inbound rules or SSH key. The proposed
resources are a dedicated VPC/subnet/route/Internet Gateway, security group,
IMDSv2 EC2 instance with an encrypted retained 30 GiB gp3 disk, and an EC2-only
SSM role, managed-policy attachment and instance profile. Public web stays OFF;
no application or credentials are auto-deployed. These are source definitions,
not resources created in the account.

The SSM policy is AmazonSSMManagedInstanceCore. The operator needs separately
approved Session Manager permissions; the instance role does not grant them to
the operator. User data ensures the Ubuntu SSM agent is enabled. T3 uses standard
CPU credits to avoid surplus-credit fees; sustained CPU load can be throttled.

Run terraform fmt -check -recursive, terraform init -backend=false,
terraform validate and terraform test here. Five synthetic-provider plan tests
cover closed default ingress, web/SSH opt-ins, storage/metadata/credit safeguards
and invalid administrator CIDRs. These mocks do not contact AWS.

For account planning, set AWS_PROFILE=flowstate-dev and provide
-var=region=us-east-2. The authenticated Ohio plan was verified with the browser-
login profile. Never run apply without the owner's explicit approval of the
specific plan, costs, deployment permissions and publication scope.

Optional SSH requires enable_admin_ssh=true plus an approved admin_cidr IPv4 /32
and PUBLIC ssh_public_key. Omit both for SSM. Existing users upgrading from the
old SSH-default configuration must review key-pair/ingress changes carefully;
do not apply against existing state casually. Both access switches manage empty
ingress explicitly when disabled so old inline rules are not left unmanaged.

Private plan files live only under ignored .tools/aws-plans with current-user
ACLs. Never publish raw plans, plan JSON, state or secret tfvars. A protected
remote backend with locking is a separate approved prerequisite for deployment.
No backend, IAM permission or cloud resource was created by planning.

See ../../docs/AWS_PLAN_REVIEW.md for current Ohio costs, proposed resources,
permission gaps and deployment gates. The separate ../terraform-managed
configuration prepares RDS/Redis/ALB/secrets. Its reference plan uses a non-secret
planning placeholder and is not apply-ready. Root disks are retained and
prevent_destroy protects the instance; cleanup always needs separate approval.
