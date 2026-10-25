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
  ingress {
    description = "Approved administrator"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
  }
  dynamic "ingress" {
    for_each = var.enable_public_web ? [80, 443] : []
    content {
      description = "Explicitly approved public web"
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_key_pair" "admin" {
  key_name_prefix = "flowstate-"
  public_key      = var.ssh_public_key
}
resource "aws_instance" "app" {
  ami                         = coalesce(var.ami_id, data.aws_ami.ubuntu.id)
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.app.id
  vpc_security_group_ids      = [aws_security_group.app.id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.admin.key_name
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
    install -d -m 0750 -o ubuntu -g ubuntu /opt/flowstate
    # Deliberately no app publication, credentials, or automatic deployment.
  USERDATA
  tags      = { Name = "flowstate-app" }
  lifecycle {
    prevent_destroy = true
  }
}
