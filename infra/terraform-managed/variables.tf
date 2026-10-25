variable "name" {
  type    = string
  default = "flowstate-managed"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,24}$", var.name))
    error_message = "Use a short lowercase resource prefix."
  }
}
variable "region" {
  type    = string
  default = "us-east-1"
}
variable "instance_type" {
  type    = string
  default = "t3.small"
}
variable "certificate_arn" {
  type        = string
  default     = null
  description = "Approved ACM certificate in the selected region."
}
variable "enable_public_web" {
  type    = bool
  default = false
  validation {
    condition     = !var.enable_public_web || can(regex("^arn:aws(-us-gov|-cn)?:acm:[a-z0-9-]+:[0-9]{12}:certificate/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.certificate_arn))
    error_message = "Public web requires an explicitly approved, valid ACM certificate ARN."
  }
}
variable "redis_auth_token" {
  type        = string
  sensitive   = true
  description = "Unique runtime Redis token. Supply securely; Terraform state stores it and must be encrypted/protected."
  validation {
    condition     = can(regex("^[A-Za-z0-9!&#$^<>-]{32,128}$", var.redis_auth_token))
    error_message = "Use 32–128 characters from the supported safe alphabet."
  }
}
