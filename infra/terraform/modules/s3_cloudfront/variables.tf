variable "name" {
  description = "Project name used to prefix all resources"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "domain" {
  description = "Root domain served by CloudFront (e.g. pokechaser.com)"
  type        = string
}

variable "zone_id" {
  description = "Route 53 hosted zone ID for DNS validation and alias records"
  type        = string
}
