output "arns" {
  description = "Map of env var name → Secrets Manager ARN for ECS task definition"
  value = {
    DJANGO_SECRET_KEY   = aws_secretsmanager_secret.secret_key.arn
    POSTGRES_HOST       = aws_secretsmanager_secret.postgres_host.arn
    POSTGRES_PASSWORD   = aws_secretsmanager_secret.postgres_password.arn
    REDIS_URL           = aws_secretsmanager_secret.redis_url.arn
    POKEMON_TCG_API_KEY = aws_secretsmanager_secret.pokemon_tcg_api_key.arn
  }
}
