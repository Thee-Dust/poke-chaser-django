# Poke Chaser — Infrastructure

Terraform-managed AWS infrastructure for `api.pokechaser.com` (Django) and `pokechaser.com` (React).

**Region:** `us-east-1`  
**IaC:** Terraform ≥ 1.6  
**State:** S3 + DynamoDB lock (`poke-chaser-terraform-state`)

---

## Directory structure

```
infra/
  terraform/
    bootstrap/              # One-time: creates S3 bucket + DynamoDB lock table
    environments/
      prod/              # Production environment root module
    modules/
      vpc/                  # VPC, subnets, NAT gateway
      rds/                  # RDS PostgreSQL 15
      elasticache/          # ElastiCache Redis 7
      ecr/                  # ECR repository (Docker images)
      ecs/                  # (Phase 2) ECS cluster, ALB, task definitions
      alb/                  # (Phase 2) Application Load Balancer
      s3_cloudfront/        # (Phase 4) Static site hosting for React
      route53/              # (Phase 2+) DNS records
```

---

## Prerequisites

- [Terraform CLI](https://developer.hashicorp.com/terraform/install) ≥ 1.6
- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) configured (`aws configure`)
- An AWS account with admin access (or a scoped IAM user)

Verify both are working:

```bash
terraform version
aws sts get-caller-identity
```

---

## Step 1 — Bootstrap remote state (one-time)

> Skip this if the S3 bucket `poke-chaser-terraform-state` already exists.

```bash
cd infra/terraform/bootstrap
terraform init
terraform apply
```

This creates:
- **S3 bucket** `poke-chaser-terraform-state` — stores `.tfstate` files
- **DynamoDB table** `poke-chaser-terraform-locks` — prevents concurrent applies

---

## Step 2 — Apply production environment

```bash
cd infra/terraform/environments/prod

# Copy the example vars file and set your DB password
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set db_password to something strong

terraform init
terraform plan
terraform apply
```

### What gets created

| Resource | Details |
|----------|---------|
| VPC | `10.0.0.0/16`, 2 public + 2 private subnets, NAT gateway |
| RDS | PostgreSQL 15, `db.t3.micro`, private subnet |
| ElastiCache | Redis 7, `cache.t3.micro`, private subnet |
| ECR | `poke-chaser-api` image repository |

### Outputs after apply

```
ecr_repository_url  = 123456789.dkr.ecr.us-east-1.amazonaws.com/poke-chaser-api
rds_endpoint        = poke-chaser-prod.xxxx.us-east-1.rds.amazonaws.com:5432
redis_endpoint      = poke-chaser-prod.xxxx.cfg.use1.cache.amazonaws.com
```

Save these — they feed into Phase 2 (ECS task environment variables).

---

## Step 3 — Phase 2: DNS, ALB, ECS, secrets, deploy pipeline

Phase 2 is split into two applies because the ACM SSL cert needs DNS to be delegated to Route 53 before it can validate.

### Step 3a — Create Route 53 hosted zone first

```bash
cd infra/terraform/environments/prod

# Add the new required vars to terraform.tfvars:
#   secret_key          = "$(openssl rand -hex 50)"
#   pokemon_tcg_api_key = "your-key-from-dev.pokemontcg.io"

terraform apply -target=module.route53
```

When complete, copy the `route53_name_servers` output (4 NS record values).

**Go to your domain registrar** and replace the nameservers for `pokechaser.com` with those 4 values. Then wait 5–30 minutes for DNS propagation.

Verify propagation before continuing:

```bash
dig NS pokechaser.com +short
# Should return the 4 Route 53 NS values
```

### Step 3b — Apply everything else

```bash
terraform apply
```

This creates:
- ACM cert for `api.pokechaser.com` (DNS-validated — takes ~1 min once NS records propagate)
- ALB + HTTPS listener + target group
- Secrets Manager entries (Django `SECRET_KEY`, DB password, Redis URL, TCG API key)
- ECS cluster + task definition + service (Django on Fargate)
- IAM OIDC provider + GitHub deploy role
- `api.pokechaser.com` → ALB Route 53 record

### Step 3c — Configure GitHub Actions

After apply, note these outputs:

```
iam_oidc_role_arn            = arn:aws:iam::...
ecs_task_security_group_id   = sg-...
ecr_repository_url           = ...dkr.ecr.us-east-1.amazonaws.com/poke-chaser-api
```

In your GitHub repo → **Settings → Secrets and variables → Actions → Variables**, add:

| Name | Value |
|------|-------|
| `AWS_DEPLOY_ROLE_ARN` | `iam_oidc_role_arn` from output |

### Step 3d — First deploy

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions `Deploy` workflow will:
1. Build and push Docker image to ECR
2. Run `manage.py migrate` as a one-off ECS task
3. Update the ECS service to the new task definition

**Gate:** `https://api.pokechaser.com/health/` returns `{"status": "ok"}`

---

## Apply order across phases

```
Phase 1  →  bootstrap → VPC → RDS → ElastiCache → ECR
Phase 2  →  route53 zone → (update nameservers) → full apply → first tag deploy
Phase 3  →  Celery worker + beat tasks → SES → Secrets Manager (email)
Phase 4  →  S3 + CloudFront (React) → Route 53 records → ACM certs
Phase 5  →  CloudWatch alarms, dashboards, cost budgets
```

---

## Tearing down

```bash
cd infra/terraform/environments/prod
terraform destroy
```

> The bootstrap state bucket must be deleted manually from the AWS console (versioned buckets cannot be destroyed by Terraform by default).
