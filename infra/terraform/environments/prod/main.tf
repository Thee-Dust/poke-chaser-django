terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ── Phase 1 ───────────────────────────────────────────────────────────────────

module "vpc" {
  source = "../../modules/vpc"

  name        = var.project_name
  environment = var.environment
}

module "ecr" {
  source = "../../modules/ecr"

  repository_name = "${var.project_name}-api"
  environment     = var.environment
}

module "rds" {
  source = "../../modules/rds"

  name               = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password

  allowed_security_group_ids = [module.ecs.task_security_group_id]
}

module "elasticache" {
  source = "../../modules/elasticache"

  name               = var.project_name
  environment        = var.environment
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  allowed_security_group_ids = [module.ecs.task_security_group_id]
}

# ── Phase 2 + 3 ───────────────────────────────────────────────────────────────

module "route53" {
  source = "../../modules/route53"

  name        = var.project_name
  environment = var.environment
  domain      = var.domain
}

module "alb" {
  source = "../../modules/alb"

  name              = var.project_name
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  zone_id           = module.route53.zone_id
  api_domain        = var.api_domain
}

module "ses" {
  source = "../../modules/ses"

  name        = var.project_name
  environment = var.environment
  aws_region  = var.aws_region

  domain  = var.domain
  zone_id = module.route53.zone_id
}

module "secrets" {
  source = "../../modules/secrets"

  name        = var.project_name
  environment = var.environment

  secret_key          = var.secret_key
  postgres_host       = split(":", module.rds.endpoint)[0]
  postgres_password   = var.db_password
  redis_endpoint      = module.elasticache.endpoint
  pokemon_tcg_api_key = var.pokemon_tcg_api_key
  ses_smtp_username   = module.ses.smtp_username
  ses_smtp_password   = module.ses.smtp_password
}

module "ecs" {
  source = "../../modules/ecs"

  name        = var.project_name
  environment = var.environment
  aws_region  = var.aws_region

  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids

  ecr_repository_url    = module.ecr.repository_url
  target_group_arn      = module.alb.target_group_arn
  alb_security_group_id = module.alb.security_group_id

  secret_arns = module.secrets.arns

  api_domain      = var.api_domain
  frontend_domain = var.domain
  db_name         = var.db_name
  db_username     = var.db_username
}

module "iam_oidc" {
  source = "../../modules/iam_oidc"

  name        = var.project_name
  environment = var.environment

  github_repo            = var.github_repo
  ecr_repository_arn     = module.ecr.repository_arn
  ecs_cluster_name       = module.ecs.cluster_name
  ecs_execution_role_arn = module.ecs.execution_role_arn
  ecs_task_role_arn      = module.ecs.task_role_arn
}

# ── Phase 4 ───────────────────────────────────────────────────────────────────

module "s3_cloudfront" {
  source = "../../modules/s3_cloudfront"

  name        = var.project_name
  environment = var.environment
  domain      = var.domain
  zone_id     = module.route53.zone_id
}

# IAM role for the React frontend repo — S3 sync + CloudFront invalidation only
resource "aws_iam_role" "github_frontend_deploy" {
  name = "${var.project_name}-github-frontend-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = module.iam_oidc.oidc_provider_arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.frontend_github_repo}:ref:refs/tags/*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_frontend_deploy" {
  name = "${var.project_name}-github-frontend-${var.environment}"
  role = aws_iam_role.github_frontend_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "S3Sync"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          module.s3_cloudfront.s3_bucket_arn,
          "${module.s3_cloudfront.s3_bucket_arn}/*"
        ]
      },
      {
        Sid      = "CloudFrontInvalidate"
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation"]
        Resource = ["arn:aws:cloudfront::*:distribution/${module.s3_cloudfront.cloudfront_distribution_id}"]
      }
    ]
  })
}

# api.pokechaser.com → ALB alias record
resource "aws_route53_record" "api" {
  zone_id = module.route53.zone_id
  name    = var.api_domain
  type    = "A"

  alias {
    name                   = module.alb.alb_dns_name
    zone_id                = module.alb.alb_zone_id
    evaluate_target_health = true
  }
}
