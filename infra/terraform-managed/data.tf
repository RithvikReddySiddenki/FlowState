resource "aws_db_subnet_group" "this" {
  name       = var.name
  subnet_ids = module.network.private_subnets
}
resource "aws_db_instance" "postgres" {
  identifier                  = var.name
  engine                      = "postgres"
  engine_version              = "17"
  instance_class              = "db.t4g.micro"
  allocated_storage           = 20
  max_allocated_storage       = 100
  storage_type                = "gp3"
  storage_encrypted           = true
  db_name                     = "flowstate"
  username                    = "flowstate_admin"
  manage_master_user_password = true
  db_subnet_group_name        = aws_db_subnet_group.this.name
  vpc_security_group_ids      = [aws_security_group.database.id]
  publicly_accessible         = false
  multi_az                    = true
  backup_retention_period     = 7
  deletion_protection         = true
  skip_final_snapshot         = false
  final_snapshot_identifier   = "${var.name}-final"
  auto_minor_version_upgrade  = true
  lifecycle { prevent_destroy = true }
}
resource "aws_elasticache_subnet_group" "this" {
  name       = var.name
  subnet_ids = module.network.private_subnets
}
resource "aws_elasticache_replication_group" "redis" {
  replication_group_id       = var.name
  description                = "FlowState private encrypted task broker"
  engine                     = "redis"
  engine_version             = "7.1"
  node_type                  = "cache.t4g.micro"
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled           = true
  subnet_group_name          = aws_elasticache_subnet_group.this.name
  security_group_ids         = [aws_security_group.cache.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_auth_token
  snapshot_retention_limit   = 1
  lifecycle { prevent_destroy = true }
}
resource "aws_secretsmanager_secret" "application" {
  name_prefix             = "${var.name}-runtime-"
  recovery_window_in_days = 30
  description             = "Runtime app configuration, populated separately; never bake into an AMI"
}
resource "aws_cloudwatch_log_group" "application" {
  name              = "/flowstate/${var.name}"
  retention_in_days = 14
}
