output "vpc_id" {
  value = module.vpc.vpc_id
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  value = module.vpc.public_subnet_ids
}

output "ecr_repository_url" {
  description = "Push Docker images here"
  value       = module.ecr.repository_url
}

output "rds_endpoint" {
  description = "PostgreSQL host — use in DATABASE_URL"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "Redis host — use in REDIS_URL"
  value       = module.elasticache.endpoint
}
