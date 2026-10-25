output "instance_id" {
  value = aws_instance.app.id
}
output "public_ip" {
  value = aws_instance.app.public_ip
}
output "ssh_command" {
  value = var.enable_admin_ssh ? "ssh ubuntu@${aws_instance.app.public_ip}" : null
}
output "ssm_command" {
  value = "aws ssm start-session --target ${aws_instance.app.id} --region ${var.region}"
}
