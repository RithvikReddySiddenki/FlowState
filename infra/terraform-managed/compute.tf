data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}
resource "aws_iam_role" "app" {
  name_prefix = "${var.name}-"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "runtime" {
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["secretsmanager:GetSecretValue"], Resource = aws_secretsmanager_secret.application.arn },
      { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.application.arn}:*" }
    ]
  })
}
resource "aws_iam_instance_profile" "app" { role = aws_iam_role.app.name }
resource "aws_instance" "app" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = module.network.public_subnets[0]
  associate_public_ip_address = true
  vpc_security_group_ids      = [aws_security_group.app.id]
  iam_instance_profile        = aws_iam_instance_profile.app.name
  credit_specification { cpu_credits = "standard" }
  metadata_options { http_tokens = "required" }
  root_block_device {
    encrypted             = true
    volume_type           = "gp3"
    volume_size           = 30
    delete_on_termination = false
  }
  user_data = <<-USERDATA
    #!/bin/bash
    set -euo pipefail
    apt-get update
    apt-get install -y ca-certificates git curl
    if ! snap list amazon-ssm-agent >/dev/null 2>&1; then snap install amazon-ssm-agent --classic; fi
    systemctl enable --now snap.amazon-ssm-agent.amazon-ssm-agent.service
    install -d -m 0750 /opt/flowstate
    # Application/secret retrieval/deployment require an explicit reviewed release.
  USERDATA
  lifecycle { prevent_destroy = true }
}
resource "aws_lb" "this" {
  name                       = var.name
  internal                   = false
  load_balancer_type         = "application"
  subnets                    = module.network.public_subnets
  security_groups            = [aws_security_group.alb.id]
  enable_deletion_protection = true
}
resource "aws_lb_target_group" "app" {
  name     = var.name
  port     = 8080
  protocol = "HTTP"
  vpc_id   = module.network.vpc_id
  health_check {
    path    = "/api/health/ready"
    matcher = "200"
  }
}
resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = aws_instance.app.id
}
resource "aws_lb_listener" "https" {
  count             = var.enable_public_web ? 1 : 0
  load_balancer_arn = aws_lb.this.arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.certificate_arn
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
resource "aws_lb_listener" "redirect" {
  count             = var.enable_public_web ? 1 : 0
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
