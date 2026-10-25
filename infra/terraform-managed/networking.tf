module "network" {
  source = "./modules/network"
  name   = var.name
}
resource "aws_security_group" "alb" {
  name_prefix = "${var.name}-alb-"
  vpc_id      = module.network.vpc_id
  ingress = [for port in(var.enable_public_web ? [80, 443] : []) : {
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
  egress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["10.60.0.0/16"]
  }
}
resource "aws_security_group" "app" {
  name_prefix = "${var.name}-app-"
  vpc_id      = module.network.vpc_id
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
resource "aws_security_group" "database" {
  name_prefix = "${var.name}-db-"
  vpc_id      = module.network.vpc_id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}
resource "aws_security_group" "cache" {
  name_prefix = "${var.name}-cache-"
  vpc_id      = module.network.vpc_id
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}
