variable "name" {
  type = string
}

variable "environment" {
  type = string
}

variable "secret_key" {
  description = "Django SECRET_KEY"
  type        = string
  sensitive   = true
}

variable "postgres_host" {
  description = "RDS endpoint (without port)"
  type        = string
}

variable "postgres_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "redis_endpoint" {
  description = "ElastiCache Redis endpoint (without port)"
  type        = string
}

variable "pokemon_tcg_api_key" {
  description = "Pokemon TCG API key from dev.pokemontcg.io"
  type        = string
  sensitive   = true
}

variable "ses_smtp_username" {
  description = "SES SMTP username (IAM access key ID)"
  type        = string
}

variable "ses_smtp_password" {
  description = "SES SMTP password (derived from IAM secret key)"
  type        = string
  sensitive   = true
}
