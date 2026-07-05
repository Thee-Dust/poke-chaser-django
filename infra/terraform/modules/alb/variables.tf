variable "name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "zone_id" {
  description = "Route 53 hosted zone ID for DNS cert validation"
  type        = string
}

variable "api_domain" {
  description = "Full domain for the API (e.g. api.pokechaser.com)"
  type        = string
}
