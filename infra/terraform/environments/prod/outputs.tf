# ── Phase 1 outputs ───────────────────────────────────────────────────────────

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
  description = "PostgreSQL host — stored in Secrets Manager as POSTGRES_HOST"
  value       = module.rds.endpoint
}

output "redis_endpoint" {
  description = "Redis host — stored in Secrets Manager as REDIS_URL"
  value       = module.elasticache.endpoint
}

# ── Phase 2 outputs ───────────────────────────────────────────────────────────

output "route53_name_servers" {
  description = "Set these at your domain registrar before running the full apply"
  value       = module.route53.name_servers
}

output "alb_dns_name" {
  value = module.alb.alb_dns_name
}

output "ecs_cluster_name" {
  value = module.ecs.cluster_name
}

output "ecs_service_name" {
  value = module.ecs.service_name
}

output "ecs_task_definition_family" {
  value = module.ecs.task_definition_family
}

output "ecs_task_security_group_id" {
  description = "Set this as ECS_SECURITY_GROUP_ID in GitHub Actions repository variables"
  value       = module.ecs.task_security_group_id
}

output "iam_oidc_role_arn" {
  description = "Set this as AWS_DEPLOY_ROLE_ARN in GitHub Actions repository variables"
  value       = module.iam_oidc.role_arn
}

# ── Phase 3 outputs ───────────────────────────────────────────────────────────

output "ecs_worker_service_name" {
  value = module.ecs.worker_service_name
}

output "ecs_beat_service_name" {
  value = module.ecs.beat_service_name
}

output "ses_smtp_endpoint" {
  description = "SES SMTP endpoint — set EMAIL_HOST to this in ECS (already wired)"
  value       = "email-smtp.${var.aws_region}.amazonaws.com"
}

# ── Phase 4 outputs ───────────────────────────────────────────────────────────

output "s3_frontend_bucket" {
  description = "S3 bucket for React build — set as S3_BUCKET in the frontend repo's GitHub variables"
  value       = module.s3_cloudfront.s3_bucket_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — set as CLOUDFRONT_DISTRIBUTION_ID in the frontend repo's GitHub variables"
  value       = module.s3_cloudfront.cloudfront_distribution_id
}

output "cloudfront_domain_name" {
  description = "CloudFront domain — use to verify the site before DNS propagates"
  value       = module.s3_cloudfront.cloudfront_domain_name
}

output "github_frontend_deploy_role_arn" {
  description = "Set as AWS_DEPLOY_ROLE_ARN in the frontend repo's GitHub variables"
  value       = aws_iam_role.github_frontend_deploy.arn
}
