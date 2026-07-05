terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source = "../../modules/vpc"

  name        = var.project_name
  environment = var.environment
}

module "ecr" {
  source = "../../modules/ecr"

  repository_name = "${var.project_name}-api"
  environment     = var.environment
}

module "rds" {
  source = "../../modules/rds"

  name               = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password
}

module "elasticache" {
  source = "../../modules/elasticache"

  name               = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
}
