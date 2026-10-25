output "instance_id" { value = aws_instance.app.id }
output "database_endpoint" { value = aws_db_instance.postgres.endpoint }
output "redis_endpoint" { value = aws_elasticache_replication_group.redis.primary_endpoint_address }
output "runtime_secret_arn" { value = aws_secretsmanager_secret.application.arn }
output "load_balancer_dns" { value = aws_lb.this.dns_name }
