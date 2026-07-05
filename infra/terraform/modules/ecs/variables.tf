variable "name" {
  type = string
}

variable "environment" {
  type = string
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "vpc_id" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "ecr_repository_url" {
  type = string
}

variable "target_group_arn" {
  type = string
}

variable "alb_security_group_id" {
  type = string
}

variable "secret_arns" {
  description = "Map of env var name → Secrets Manager ARN"
  type        = map(string)
}

variable "api_domain" {
  description = "API domain (e.g. api.pokechaser.com)"
  type        = string
}

variable "frontend_domain" {
  description = "Frontend domain (e.g. pokechaser.com)"
  type        = string
}

variable "db_name" {
  type    = string
  default = "pokechaser"
}

variable "db_username" {
  type    = string
  default = "pokechaser"
}

variable "cpu" {
  type    = number
  default = 256
}

variable "memory" {
  type    = number
  default = 512
}

variable "desired_count" {
  type    = number
  default = 1
}
