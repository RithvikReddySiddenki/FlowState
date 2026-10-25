# Plan-time synthetic values exercise our configuration, not AWS API validity.
mock_provider "aws" {
  override_during = plan
  mock_data "aws_ami" {
    defaults = { id = "ami-00000000000000001" }
  }
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-1a", "us-east-1b"] }
  }
  mock_resource "aws_secretsmanager_secret" {
    defaults = { arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:synthetic-runtime" }
  }
  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:us-east-1:123456789012:log-group:/flowstate/synthetic" }
  }
  override_resource {
    target = aws_security_group.app
    values = { id = "sg-00000000000000001" }
  }
  override_resource {
    target = aws_security_group.alb
    values = { id = "sg-00000000000000002" }
  }
}

variables {
  redis_auth_token = "synthetic-test-token-not-for-deployment-1234"
}

run "isolated_managed_data" {
  command = plan
  assert {
    condition     = !aws_db_instance.postgres.publicly_accessible && aws_db_instance.postgres.storage_encrypted && aws_db_instance.postgres.multi_az && aws_db_instance.postgres.deletion_protection && !aws_db_instance.postgres.skip_final_snapshot
    error_message = "RDS must remain private, encrypted, redundant and deletion protected."
  }
  assert {
    condition     = aws_elasticache_replication_group.redis.transit_encryption_enabled && aws_elasticache_replication_group.redis.at_rest_encryption_enabled && aws_elasticache_replication_group.redis.automatic_failover_enabled && aws_elasticache_replication_group.redis.num_cache_clusters == 2
    error_message = "Redis must use TLS, encryption and redundant failover nodes."
  }
  assert {
    condition     = length(aws_security_group.alb.ingress) == 0 && length(aws_lb_listener.https) == 0 && length(aws_lb_listener.redirect) == 0
    error_message = "No public ingress/listener is allowed by default."
  }
  assert {
    condition     = alltrue([for rule in aws_security_group.app.ingress : rule.from_port == 8080 && rule.to_port == 8080 && rule.security_groups == toset([aws_security_group.alb.id])]) && alltrue([for rule in aws_security_group.database.ingress : rule.from_port == 5432 && rule.security_groups == toset([aws_security_group.app.id])]) && alltrue([for rule in aws_security_group.cache.ingress : rule.from_port == 6379 && rule.security_groups == toset([aws_security_group.app.id])])
    error_message = "App/data ingress must come only from the designated upstream security group."
  }
  assert {
    condition     = length(jsondecode(aws_iam_role_policy.runtime.policy).Statement) == 2 && jsondecode(aws_iam_role_policy.runtime.policy).Statement[0].Resource == aws_secretsmanager_secret.application.arn && jsondecode(aws_iam_role_policy.runtime.policy).Statement[0].Action == ["secretsmanager:GetSecretValue"] && toset(jsondecode(aws_iam_role_policy.runtime.policy).Statement[1].Action) == toset(["logs:CreateLogStream", "logs:PutLogEvents"]) && jsondecode(aws_iam_role_policy.runtime.policy).Statement[1].Resource == "${aws_cloudwatch_log_group.application.arn}:*"
    error_message = "The application may read only its runtime secret, never wildcard or RDS admin secrets."
  }
  assert {
    condition     = aws_instance.app.metadata_options[0].http_tokens == "required" && aws_instance.app.root_block_device[0].encrypted && !aws_instance.app.root_block_device[0].delete_on_termination && aws_instance.app.credit_specification[0].cpu_credits == "standard" && aws_db_instance.postgres.manage_master_user_password && aws_db_instance.postgres.backup_retention_period >= 7
    error_message = "Compute must require IMDSv2/encrypted retained storage, and RDS must manage its admin password and retain backups."
  }
}

run "reject_missing_public_certificate" {
  command = plan
  variables { enable_public_web = true }
  expect_failures = [var.enable_public_web]
}

run "reject_empty_public_certificate" {
  command = plan
  variables {
    enable_public_web = true
    certificate_arn   = ""
  }
  expect_failures = [var.enable_public_web]
}

run "approved_certificate_opt_in" {
  command = plan
  variables {
    enable_public_web = true
    certificate_arn   = "arn:aws:acm:us-east-1:123456789012:certificate/00000000-0000-0000-0000-000000000001"
  }
  assert {
    condition     = length(aws_lb_listener.https) == 1 && length(aws_lb_listener.redirect) == 1 && toset([for rule in aws_security_group.alb.ingress : rule.from_port]) == toset([80, 443])
    error_message = "Public opt-in requires the HTTPS listener and HTTP-to-HTTPS redirect only."
  }
}

run "reject_weak_broker_token" {
  command = plan
  variables { redis_auth_token = "short" }
  expect_failures = [var.redis_auth_token]
}
