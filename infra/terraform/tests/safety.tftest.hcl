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
    condition     = length(aws_security_group.app.ingress) == 0 && length(aws_key_pair.admin) == 0
    error_message = "Default SSM administration must require no inbound ports or SSH keys."
  }
  assert {
    condition     = aws_instance.app.metadata_options[0].http_tokens == "required" && aws_instance.app.root_block_device[0].encrypted && !aws_instance.app.root_block_device[0].delete_on_termination && aws_instance.app.credit_specification[0].cpu_credits == "standard"
    error_message = "Instance metadata must require tokens and its encrypted disk must be retained."
  }
}

run "explicit_web_opt_in" {
  command = plan
  variables { enable_public_web = true }
  assert {
    condition     = toset([for rule in aws_security_group.app.ingress : rule.from_port]) == toset([80, 443])
    error_message = "Web opt-in must not implicitly open SSH."
  }
}

run "reject_worldwide_ssh" {
  command = plan
  variables {
    enable_admin_ssh = true
    admin_cidr       = "0.0.0.0/0"
  }
  expect_failures = [var.admin_cidr]
}

run "reject_ipv6_as_ipv4_administrator" {
  command = plan
  variables {
    enable_admin_ssh = true
    admin_cidr       = "2001:db8::/32"
  }
  expect_failures = [var.admin_cidr]
}
run "restricted_ssh_opt_in" {
  command = plan
  variables { enable_admin_ssh = true }
  assert {
    condition     = length(aws_key_pair.admin) == 1 && length(aws_security_group.app.ingress) == 1 && alltrue([for rule in aws_security_group.app.ingress : rule.from_port == 22 && toset(rule.cidr_blocks) == toset([var.admin_cidr])])
    error_message = "Explicit SSH must remain limited to the administrator IPv4 /32."
  }
}
