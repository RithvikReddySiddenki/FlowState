# Ohio infrastructure plan review

Prepared 2026-10-25. Profile flowstate-dev; region us-east-2 (Ohio).
AWS CLI 2.38.5 browser login was verified by STS as the IAM user
flowstate-developer, not root. Attached policies observed: ViewOnlyAccess,
SignInLocalDevelopmentAccess and IAMUserChangePassword; no inline user policies
or group memberships. Account number and real ARNs are retained only in private
local diagnostics, not this repository.

## What was actually verified

Both directories passed terraform init -backend=false, fmt, validate and ten
synthetic plan tests (five each). Authenticated real plans succeeded with the
existing view-only profile: simple 10 creates, managed 30 creates, zero updates or
deletes. The plans use empty local state and do not import/adopt pre-existing account resources. This was not an apply. No resources, IAM changes, budgets or paid builds
were created. t3.small is offered in Ohio; PostgreSQL17 Multi-AZ db.t4g.micro is
orderable. No proposed CIDR overlap was found with the account's visible VPC IPv4
ranges. Current EC2 vCPU quota could not be read with this principal.

## Alternatives

**Simple:** one t3.small Ubuntu24.04 x86_64 EC2; encrypted retained 30GiB gp3 disk;
10.42.0.0/16 VPC, subnet, Internet Gateway, public route/table association;
security group; EC2 SSM role, managed-policy attachment and instance profile.
There is no NAT, ALB, RDS or hosted DNS. PostgreSQL/Redis run in the private
Compose network on this single host after a separately approved app deployment.
The EC2 root disk is part of aws_instance, not an extra Terraform resource.
This is a single failure domain and needs approved backup/restore operations.

**Managed reference:** one t3.small compute instance; two-AZ VPC 10.60.0.0/16 with
four subnets, Internet Gateway, route tables/associations; four security groups;
private Multi-AZ PostgreSQL17 db.t4g.micro (20GiB gp3, seven-day backups,
AWS-managed admin password); two encrypted Redis7.1 cache.t4g.micro nodes with
failover; DB/cache subnet groups; ALB, target group/attachment; runtime secret;
CloudWatch group; app role, policies and profile. Data is redundant; compute
remains one instance and is not fully HA. No public listeners are planned.
Managed-service-linked roles may be created implicitly on first use; their
existence could not be inspected because iam:GetRole was denied. They are not
included in the 30 Terraform objects and do not add a direct IAM service charge.

The managed binary contains a deliberately non-secret, planning-only Redis
placeholder. DO NOT APPLY IT. Establish protected state and secret delivery,
replace the placeholder securely and regenerate/review before approval.

## Monthly estimate (USD)

730 running hours, public on-demand Linux prices retrieved 2026-10-25 for Ohio.
No free-tier credits, discounts or tax assumed. Fixed provisioned estimate:

| Component | Simple | Managed reference |
|---|---:|---:|
| EC2 t3.small Linux | USD 15.18 | USD 15.18 |
| 30 GiB EC2 gp3 root disk | USD 2.40 | USD 2.40 |
| Public IPv4 (one EC2; managed adds two ALB addresses) | USD 3.65 | USD 10.95 |
| RDS db.t4g.micro Multi-AZ pair | - | USD 23.36 |
| 20 GiB RDS Multi-AZ gp3 | - | USD 4.60 |
| Two Redis cache.t4g.micro nodes | - | USD 23.36 |
| Application Load Balancer | - | USD 16.43 |
| Two Secrets Manager secrets (runtime and RDS admin) | - | USD 0.80 |
| **Provisioned baseline** | **USD 21.23** | **USD 97.08** |

Example additional usage/backup allowances (not a usage cap):

| Component | Simple | Managed reference |
|---|---:|---:|
| Example billable internet egress beyond any free allowance | USD 0.90 | USD 0.90 |
| Optional retained 30 GiB EBS snapshot (not provisioned by plan) | USD 1.50 | USD 1.50 |
| Example one average ALB LCU | - | USD 5.84 |
| Example log ingestion | - | USD 2.50 |
| Example one GiB retained compressed logs | - | USD 0.03 |
| Example 1,000 secret API calls | - | USD 0.01 |
| Example 20 billable cross-AZ endpoint-GB | - | USD 0.20 |
| **Baseline plus example allowances** | **USD 23.63** | **USD 108.05** |

Assumptions:10 billable GB internet egress after any account-wide free allowance;
managed averages one ALB LCU,5GiB log ingestion/oneGiB retained compressed logs,
1,000 secret requests and20 billable cross-AZ endpoint-GB. RDS Multi-AZ rates
already include the standby; Redis pricing is per node. Public IPv4 assumes one
EC2 address plus at least two ALB addresses for managed; scaling may add addresses.
Two stored secrets are budgeted for managed (app runtime and RDS-managed admin).
The optional30GiB EBS snapshot is a budget allowance, not a resource configured by
these plans. RDS replication is not added as ordinary application cross-AZ traffic.

Totals sum unrounded decimal rates. The rate snapshot records AWS SKU, source
URL, publication date and unit for every price:
[pricing snapshot](../infra/pricing/us-east-2-2026-10-25.json).
Reproduce with `python -m scripts.estimate_aws_costs`; change --hours,
--billable-egress-gb or --log-ingest-gb to model different usage. No billing API
or AWS credentials are used by this calculator. For an updated estimate refresh
public rates first. Pricing API access (pricing:GetProducts) was denied; public
AWS catalogs supplied the same SKU/rate evidence without changing permissions.

Excluded/variable: domain registration/DNS, state-backend storage/requests,
optional extra snapshots and backup exports, extra API/transfer/log usage,
RDS storage auto-growth above 20 GiB (configured ceiling 100 GiB), extra ALB IPv4s,
RDS surplus CPU credits, assessment/verification services, taxes and support plans. RDS T4g runs in Unlimited mode and may add CPU-credit charges above baseline; the example assumes none. See [RDS PostgreSQL pricing](https://aws.amazon.com/rds/postgresql/pricing/). Standard EC2 T3 credits
avoid surplus-credit fees but may throttle sustained workloads. Stopping compute
does not stop disk/retained-backup charges. Confirm the detailed estimate in the
[AWS calculator](https://calculator.aws/) before purchase/deployment.

## Security/configuration review

- SSH and web ingress are OFF by default. Both configurations manage ingress=[]
  explicitly when disabled, so an omitted block cannot leave rules unmanaged.
  Simple SSH remains a separate opt-in requiring a single IPv4 /32 and public key.
- EC2 uses IMDSv2, encrypted retained root storage, standard CPU credits and an
  EC2-only trust policy. User data enables SSM, not the app or credentials.
- Managed app8080 accepts only the ALB security group; DB5432/cache6379 accept
  only the app group. RDS/cache are in private subnets. There is no NAT charge;
  compute uses an outbound public IPv4. Outbound egress is broad for package,
  image, OAuth and Gmail access and should be reviewed before production.
- Managed RDS/cache encrypt storage/transport and have backups/failover. Lifecycle
  and deletion protections remain. RDS auto-growth has a cost ceiling to review.
- The managed runtime secret policy is scoped to that app secret; the EC2 role
  cannot read the RDS admin secret via that policy. AmazonSSMManagedInstanceCore
  is also attached and should be reviewed as a separate host-management policy.
- State still needs an approved encrypted/locked backend before deployment. Real
  Redis tokens would be in state; sensitive=true is not state encryption.
- SSM operator rights are separate from the instance role. CLI sessions also need
  the Session Manager plugin locally, or use the AWS console with approved rights.

## Permissions: what is missing and why

No additional permissions were required to complete these plans. The current
policies do not authorize resource creation, role creation or Session Manager
administration. No mutation was attempted to prove this; identity policy metadata
was read. IAM principal simulation was itself denied (iam:SimulatePrincipalPolicy).

The deterministic IAM Policy Autopilot0.3.0 analysis uses only sanitized resource
types/actions, synthetic account123456789012 and disabled telemetry. Its complete
review outputs are [simple](../infra/iam/simple-autopilot-review.json) and
[managed](../infra/iam/managed-reference-autopilot-review.json). They are NOT
least-privilege or attach-ready policies: the provider-handler analysis includes
unnecessary operations (for example unrelated IAM tag operations/deletion paths)
and wildcard resources. An administrator must refine scope/conditions and review
provider/first-use dependencies; do not attach these drafts wholesale.

Confirmed deployment capability gaps include:

| Purpose | Relevant additional actions from the generated baseline |
|---|---|
| EC2/VPC provisioning | ec2:RunInstances, ec2:CreateVpc, ec2:CreateSubnet, ec2:CreateInternetGateway, ec2:AttachInternetGateway, ec2:CreateRouteTable, ec2:CreateRoute, ec2:AssociateRouteTable, ec2:CreateSecurityGroup, ec2:AuthorizeSecurityGroupIngress, ec2:AuthorizeSecurityGroupEgress, ec2:RevokeSecurityGroupIngress, ec2:RevokeSecurityGroupEgress, ec2:CreateTags, ec2:ModifyVpcAttribute |
| EC2 SSM profile | iam:CreateRole, iam:CreateInstanceProfile, iam:AddRoleToInstanceProfile, iam:AttachRolePolicy, iam:TagRole, iam:TagInstanceProfile, iam:PassRole; iam:GetRole/iam:GetInstanceProfile and related list/read operations for refresh |
| Managed data | rds:CreateDBInstance, rds:CreateDBSubnetGroup and the generated RDS/ElastiCache/KMS actions in the managed baseline |
| ALB/logs/secrets | Generated elasticloadbalancing, logs and secretsmanager actions in the managed baseline |

Scope deployment IAM rights to FlowState role/profile names; restrict
PassRole to those roles and iam:PassedToService=ec2.amazonaws.com. Restrict
AttachRolePolicy to the reviewed SSM managed policy. Do not grant AdministratorAccess
as a shortcut. Prefer an explicitly approved deployment role over expanding this
view-only IAM user. Provider-handler baselines are an overapproximation, not a
claim that all101/159 generated actions are strictly necessary.

For managed first-use service roles, an administrator must either ensure the
roles already exist or authorize iam:CreateServiceLinkedRole for the specific
services. ElastiCache's documented setup also uses iam:PutRolePolicy. Scope to
the relevant aws-service-role paths and iam:AWSServiceName values:
[ELB](https://docs.aws.amazon.com/elasticloadbalancing/latest/userguide/elb-service-linked-roles.html),
[RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAM.ServiceLinkedRoles.html),
[ElastiCache](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/using-service-linked-roles.html).
These implicit prerequisites are not covered by the generated baselines.

Operator session rights are separately scoped ssm:StartSession to the selected
instance/document, ssmmessages:OpenDataChannel and ssm:ResumeSession/TerminateSession
to the operator's own sessions. Follow the
[AWS Session Manager examples](https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-restrict-access-quickstart.html).
Secure configuration/migration delivery may need separately approved operations;
operator SSH is not implicitly enabled.

Optional review-only reads: pricing:GetProducts (live query pricing),
iam:SimulatePrincipalPolicy (permission simulation), iam:GetRole (role inspection)
and service-quotas:GetServiceQuota (available EC2 quota) were denied. None is a
reason to grant deployment write access just to view this report. An administrator
must verify at least two available standard on-demand vCPUs before launch.

## Deployment decision and steps

1. Choose simple or managed and approve a spending envelope/usage assumptions.
2. Have the administrator review/scoped grant a deployment role and operator
   session access. No permissions were changed by this work.
3. Establish protected state/locking and backup/secret delivery. For managed,
   replace the planning placeholder securely and generate a fresh plan.
4. Reverify identity/profile/region, run validation/tests and a fresh saved plan.
   Review the exact resource actions, AMI, cost assumptions and hash. Approval of
   this report alone is not permission to run apply.
5. Only after explicit approval apply the reviewed plan using authorized credentials.
   Verify SSM, private service health and retained/encrypted storage.
6. Deploy the pinned reviewed app release using the runbook, with separately
   delivered production secrets and approved migrations/backups. Do not copy the
   local DB/refresh tokens or development keys without a separate reviewed process.
7. Keep public access off until a domain/certificate, HTTPS renewal, production
   OAuth callback and publication scope are approved. Then verify actual login,
   Gmail, CRUD/recovery and monitoring in the deployed environment.
8. Any future teardown/deletion/protection bypass needs separate approval.

## Private plan artifacts

The binary plans and private actual-account-bound permission-review copies live in .tools/aws-plans under current-user-only ACLs. Placeholder ARN substitution was done by trusted local JSON processing after sanitized analysis; no real account identity was passed to the analyzer. Raw plan
JSON/logs and account details are ignored and never committed. Review locally;
regenerate if inputs, credentials, provider/state or configuration change. The
managed placeholder makes that plan reference-only regardless of its hash.

- simple: 10 creates, zero updates/deletes; public Ubuntu AMI ami-0fc53b217ec1ad816; SHA256 1f8e582c4ed1407ed88b328d71f2b627b8614992d3ea2cab43d4ad9b20630b6e.
- managed-reference: 30 creates, zero updates/deletes; public Ubuntu AMI ami-0fc53b217ec1ad816; SHA256 20dca31560d71f49930a517691a8e7d171fa62a2f6fb34e3482aeb7db55ff303.

Policy-analysis command (sanitized input only; telemetry disabled):

```powershell
$env:DISABLE_IAM_POLICY_AUTOPILOT_TELEMETRY = "true"
uvx iam-policy-autopilot@0.3.0 generate-policies "$PWD/.tools/simple-sanitized-plan.json" --region us-east-2 --account 123456789012 --pretty
```

Use only the sanitized type/action file with the synthetic account. Full plan
analysis was rejected by automatic approval review; the safer sanitized approach
succeeded. No full plan or real account configuration was supplied to that tool.
Keep generated output local until reviewed; never use an upload/apply option.


## Verified development checkpoint

Pushed0cecf5c (infrastructure defaults) and8ddb152 (estimator/review artifacts).
54 SQLite/PostgreSQL tests, ten Terraform safety tests and all seven CI jobs pass:
https://github.com/RithvikReddySiddenki/FlowState/actions/runs/40244007184 .
No AWS mutation was executed. Raw state/plans/credentials remain outside Git;
source scanning found no current credential values or real account number in
the proposed tracked artifacts. The user's unrelated .vscode/ stays untracked.
