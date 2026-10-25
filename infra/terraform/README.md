# Initial EC2 deployment

This creates a dedicated VPC, subnet, route, restricted SSH security group,
encrypted persistent root disk, key pair and EC2 instance. Database/Redis ports
are never opened. Web ingress defaults OFF. No application is auto-deployed.
No IAM role is created because the base app requires no AWS API permissions.
IMDSv2 is required; see [AWS metadata guidance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configuring-instance-metadata-options.html).

Install Terraform, run `terraform fmt -check`, `terraform init -backend=false`
and `terraform validate` here. Copy terraform.tfvars.example to ignored
terraform.tfvars with your approved IP and PUBLIC key. Configure AWS access
outside this repo, preferably `aws configure sso`, then `aws sso login`.
Run `terraform plan` only with the intended profile/region and reviewed values.
Never publish plan output or state; both can contain sensitive infrastructure data.
For shared use configure a separately approved encrypted remote backend with
locking. The local default is for evaluation, not team production state.

STOP before apply: user must approve resources, estimated costs, public IP and
the specific plan. Do not run destroy or disable prevent_destroy without approval.
Even an idle instance incurs compute, EBS and public IPv4 charges; data transfer,
snapshots and DNS/TLS operations may add costs. No price estimate or free-tier
eligibility is assumed. Avoid a paid NAT/ALB for this single-host starting stage.
The root disk is retained on instance termination and needs approved lifecycle
management; resource deletion is not a backup strategy.

The separate [managed-services architecture](../terraform-managed/README.md)
prepares private RDS/ElastiCache, ALB, runtime secrets and CloudWatch. Both
configurations validate; neither has been planned/applied against an AWS account.
