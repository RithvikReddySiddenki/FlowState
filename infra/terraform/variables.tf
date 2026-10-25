variable "region" {
  type    = string
  default = "us-east-1"
}
variable "instance_type" {
  type    = string
  default = "t3.small"
}
variable "ssh_public_key" {
  type        = string
  description = "Public SSH key only; never provide a private key."
  default     = null
  validation {
    condition     = !var.enable_admin_ssh || can(regex("^(ssh-ed25519|ssh-rsa) ", var.ssh_public_key))
    error_message = "Supply an OpenSSH public key."
  }
}
variable "admin_cidr" {
  type        = string
  description = "Approved single IPv4 administrator address as /32."
  default     = null
  validation {
    condition     = !var.enable_admin_ssh || (can(cidrnetmask(var.admin_cidr)) && can(regex("/32$", var.admin_cidr)) && var.admin_cidr != "0.0.0.0/32")
    error_message = "SSH requires a specific approved IPv4 /32."
  }
}
variable "enable_admin_ssh" {
  type        = bool
  default     = false
  description = "Optional restricted SSH; defaults to SSM administration without inbound ports or keys."
}
variable "enable_public_web" {
  type        = bool
  default     = false
  description = "Enable 80/443 ingress only after explicit publication approval and TLS setup."
}
variable "ami_id" {
  type        = string
  default     = null
  description = "Optional reviewed Ubuntu 24.04 x86_64 AMI override."
}
