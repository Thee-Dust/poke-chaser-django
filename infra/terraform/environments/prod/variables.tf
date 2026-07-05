variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used to prefix all resources"
  type        = string
  default     = "poke-chaser"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "db_name" {
  description = "RDS database name"
  type        = string
  default     = "pokechaser"
}

variable "db_username" {
  description = "RDS master username"
  type        = string
  default     = "pokechaser"
}

variable "db_password" {
  description = "RDS master password — set this in terraform.tfvars (not committed)"
  type        = string
  sensitive   = true
}
