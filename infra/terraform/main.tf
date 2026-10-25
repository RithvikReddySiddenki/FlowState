data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical public image publisher, not a personal account.
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}
resource "aws_vpc" "app" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
}
resource "aws_subnet" "app" {
  vpc_id     = aws_vpc.app.id
  cidr_block = "10.42.1.0/24"
}
resource "aws_internet_gateway" "app" {
  vpc_id = aws_vpc.app.id
}
resource "aws_route_table" "app" {
  vpc_id = aws_vpc.app.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.app.id
  }
}
resource "aws_route_table_association" "app" {
  subnet_id      = aws_subnet.app.id
  route_table_id = aws_route_table.app.id
}
resource "aws_security_group" "app" {
  name_prefix = "flowstate-"
  description = "Admin SSH and explicitly approved web access only"
  vpc_id      = aws_vpc.app.id
  # Manage [] explicitly so disabling access also removes previously managed rules.
  ingress = concat(
    var.enable_admin_ssh ? [{
      description      = "Approved administrator"
      from_port        = 22
      to_port          = 22
      protocol         = "tcp"
      cidr_blocks      = [var.admin_cidr]
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      security_groups  = []
      self             = false
    }] : [],
    [for port in(var.enable_public_web ? [80, 443] : []) : {
      description      = "Explicitly approved public web"
      from_port        = port
      to_port          = port
      protocol         = "tcp"
      cidr_blocks      = ["0.0.0.0/0"]
      ipv6_cidr_blocks = []
      prefix_list_ids  = []
      security_groups  = []
      self             = false
    }]
  )
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_key_pair" "admin" {
  count           = var.enable_admin_ssh ? 1 : 0
  key_name_prefix = "flowstate-"
  public_key      = var.ssh_public_key
}
resource "aws_iam_role" "ssm" {
  name_prefix = "flowstate-ssm-"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ssm.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_instance_profile" "ssm" {
  name_prefix = "flowstate-ssm-"
  role        = aws_iam_role.ssm.name
}
resource "aws_instance" "app" {
  ami                         = coalesce(var.ami_id, data.aws_ami.ubuntu.id)
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.app.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  associate_public_ip_address = true
  key_name                    = var.enable_admin_ssh ? aws_key_pair.admin[0].key_name : null
  iam_instance_profile        = aws_iam_instance_profile.ssm.name
  credit_specification { cpu_credits = "standard" }
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }
  root_block_device {
    volume_type           = "gp3"
    volume_size           = 30
    encrypted             = true
    delete_on_termination = false
  }
  user_data = <<-USERDATA
    #!/bin/bash
    set -euo pipefail
    apt-get update
    apt-get install -y ca-certificates curl git
    if ! snap list amazon-ssm-agent >/dev/null 2>&1; then snap install amazon-ssm-agent --classic; fi
    systemctl enable --now snap.amazon-ssm-agent.amazon-ssm-agent.service
    install -d -m 0750 -o ubuntu -g ubuntu /opt/flowstate
    # Deliberately no app publication, credentials, or automatic deployment.
  USERDATA
  tags      = { Name = "flowstate-app" }
  lifecycle {
    prevent_destroy = true
  }
}
