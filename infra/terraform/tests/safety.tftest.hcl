# Synthetic provider only: no AWS account, API calls, resources or real secrets.
mock_provider "aws" {
  override_during = plan
  mock_data "aws_ami" {
    defaults = { id = "ami-00000000000000001" }
  }
}

variables {
  admin_cidr     = "192.0.2.10/32"
  ssh_public_key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAISyntheticTestKeyNotForRealDeployment"
}

run "private_defaults" {
  command = plan
  assert {
    condition     = length(aws_security_group.app.ingress) == 1 && alltrue([for rule in aws_security_group.app.ingress : rule.from_port == 22 && rule.to_port == 22 && toset(rule.cidr_blocks) == toset([var.admin_cidr])])
    error_message = "Default ingress must permit only the administrator's SSH /32."
  }
  assert {
    condition     = aws_instance.app.metadata_options[0].http_tokens == "required" && aws_instance.app.root_block_device[0].encrypted && !aws_instance.app.root_block_device[0].delete_on_termination
    error_message = "Instance metadata must require tokens and its encrypted disk must be retained."
  }
}

run "explicit_web_opt_in" {
  command = plan
  variables { enable_public_web = true }
  assert {
    condition     = toset([for rule in aws_security_group.app.ingress : rule.from_port]) == toset([22, 80, 443])
    error_message = "Explicit web opt-in may add only HTTP/HTTPS to administrator SSH."
  }
}

run "reject_worldwide_ssh" {
  command = plan
  variables { admin_cidr = "0.0.0.0/0" }
  expect_failures = [var.admin_cidr]
}

run "reject_ipv6_as_ipv4_administrator" {
  command = plan
  variables { admin_cidr = "2001:db8::/32" }
  expect_failures = [var.admin_cidr]
}
