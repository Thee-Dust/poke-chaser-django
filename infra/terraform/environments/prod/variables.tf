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

# ── Database ──────────────────────────────────────────────────────────────────

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
  description = "RDS master password — set in terraform.tfvars (never commit)"
  type        = string
  sensitive   = true
}

# ── Application secrets ───────────────────────────────────────────────────────

variable "secret_key" {
  description = "Django SECRET_KEY — generate with: openssl rand -hex 50"
  type        = string
  sensitive   = true
}

variable "pokemon_tcg_api_key" {
  description = "Pokemon TCG API key from https://dev.pokemontcg.io"
  type        = string
  sensitive   = true
}

# ── Domains ───────────────────────────────────────────────────────────────────

variable "domain" {
  description = "Root domain (e.g. pokechaser.com)"
  type        = string
  default     = "pokechaser.com"
}

variable "api_domain" {
  description = "API subdomain (e.g. api.pokechaser.com)"
  type        = string
  default     = "api.pokechaser.com"
}

# ── GitHub / CD ───────────────────────────────────────────────────────────────

variable "github_repo" {
  description = "GitHub repository in org/repo format"
  type        = string
  default     = "Thee-Dust/poke-chaser-django"
}
