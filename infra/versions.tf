terraform {
  required_version = ">= 1.10, < 2.0"
  cloud {
    organization = "peach-lab7"
    workspaces { name = "peach-dev" }
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# The migration workspace uses remote execution in HCP Terraform.
# Credentials come from HCP's short-lived AWS workload identity, never this file.
provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}
