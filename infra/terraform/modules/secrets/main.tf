locals {
  redis_url = "redis://${var.redis_endpoint}:6379/0"
}

resource "aws_secretsmanager_secret" "secret_key" {
  name                    = "${var.name}/${var.environment}/secret-key"
  recovery_window_in_days = 0

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "secret_key" {
  secret_id     = aws_secretsmanager_secret.secret_key.id
  secret_string = var.secret_key
}

resource "aws_secretsmanager_secret" "postgres_host" {
  name                    = "${var.name}/${var.environment}/postgres-host"
  recovery_window_in_days = 0

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "postgres_host" {
  secret_id     = aws_secretsmanager_secret.postgres_host.id
  secret_string = var.postgres_host
}

resource "aws_secretsmanager_secret" "postgres_password" {
  name                    = "${var.name}/${var.environment}/postgres-password"
  recovery_window_in_days = 0

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "postgres_password" {
  secret_id     = aws_secretsmanager_secret.postgres_password.id
  secret_string = var.postgres_password
}

resource "aws_secretsmanager_secret" "redis_url" {
  name                    = "${var.name}/${var.environment}/redis-url"
  recovery_window_in_days = 0

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "redis_url" {
  secret_id     = aws_secretsmanager_secret.redis_url.id
  secret_string = local.redis_url
}

resource "aws_secretsmanager_secret" "pokemon_tcg_api_key" {
  name                    = "${var.name}/${var.environment}/pokemon-tcg-api-key"
  recovery_window_in_days = 0

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "pokemon_tcg_api_key" {
  secret_id     = aws_secretsmanager_secret.pokemon_tcg_api_key.id
  secret_string = var.pokemon_tcg_api_key
}
