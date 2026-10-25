provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project   = "FlowState"
      ManagedBy = "Terraform"
    }
  }
}
