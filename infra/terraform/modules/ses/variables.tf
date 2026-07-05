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

variable "domain" {
  description = "Domain to verify in SES (e.g. pokechaser.com)"
  type        = string
}

variable "zone_id" {
  description = "Route 53 hosted zone ID for the domain"
  type        = string
}
