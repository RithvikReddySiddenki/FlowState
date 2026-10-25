packer {
  required_plugins {
    amazon = {
      source  = "github.com/hashicorp/amazon"
      version = ">= 1.3.0, < 2.0.0"
    }
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
source "amazon-ebs" "ubuntu" {
  region        = var.region
  instance_type = var.instance_type
  ssh_username  = "ubuntu"
  ami_name      = "flowstate-docker-{{timestamp}}"
  encrypt_boot  = true
  source_ami_filter {
    filters = {
      name                = "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"
      root-device-type    = "ebs"
      virtualization-type = "hvm"
    }
    owners      = ["099720109477"]
    most_recent = true
  }
  metadata_options {
    http_tokens = "required"
  }
  tags = { Project = "FlowState", Purpose = "Docker baseline" }
}
build {
  sources = ["source.amazon-ebs.ubuntu"]
  provisioner "shell" {
    inline = ["sudo cloud-init status --wait", "sudo apt-get update", "sudo apt-get upgrade -y"]
  }
  provisioner "shell" {
    script          = "${path.root}/../../scripts/bootstrap-ubuntu.sh"
    execute_command = "chmod +x {{ .Path }}; sudo {{ .Path }} --approved"
  }
  provisioner "shell" {
    inline = ["sudo apt-get clean", "sudo rm -f /var/log/cloud-init-output.log"]
  }
}
