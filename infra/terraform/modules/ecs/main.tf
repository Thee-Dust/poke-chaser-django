resource "aws_ecs_cluster" "main" {
  name = "${var.name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "${var.name}-cluster"
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.name}-${var.environment}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.name}-worker-${var.environment}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_log_group" "beat" {
  name              = "/ecs/${var.name}-beat-${var.environment}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
  }
}

locals {
  common_environment = [
    { name = "DJANGO_DEBUG", value = "False" },
    { name = "DJANGO_ALLOWED_HOSTS", value = var.api_domain },
    { name = "FRONTEND_URL", value = "https://${var.frontend_domain}" },
    { name = "CORS_ALLOWED_ORIGINS", value = "https://${var.frontend_domain}" },
    { name = "CSRF_TRUSTED_ORIGINS", value = "https://${var.frontend_domain}" },
    { name = "POSTGRES_DB", value = var.db_name },
    { name = "POSTGRES_USER", value = var.db_username },
    { name = "POSTGRES_PORT", value = "5432" },
    { name = "EMAIL_HOST", value = "email-smtp.${var.aws_region}.amazonaws.com" },
    { name = "EMAIL_PORT", value = "587" },
    { name = "EMAIL_USE_TLS", value = "True" },
    { name = "DEFAULT_FROM_EMAIL", value = "noreply@${var.frontend_domain}" },
  ]

  common_secrets = [
    for env_name, arn in var.secret_arns : {
      name      = env_name
      valueFrom = arn
    }
  ]
}

resource "aws_iam_role" "execution" {
  name = "${var.name}-ecs-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  name = "${var.name}-secrets-${var.environment}"
  role = aws_iam_role.execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = values(var.secret_arns)
    }]
  })
}

resource "aws_iam_role" "task" {
  name = "${var.name}-ecs-task-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_security_group" "tasks" {
  name        = "${var.name}-ecs-tasks-${var.environment}"
  description = "ECS tasks  allow 8000 from ALB"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.name}-ecs-tasks-sg"
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "${var.name}-api-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "api"
      image     = "${var.ecr_repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      command = [
        "gunicorn",
        "pokechaser.wsgi:application",
        "--bind", "0.0.0.0:8000",
        "--workers", "3"
      ]

      environment = local.common_environment
      secrets     = local.common_secrets

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecs_service" "api" {
  name            = "${var.name}-api-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "api"
    container_port   = 8000
  }

  health_check_grace_period_seconds = 120

  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [aws_iam_role_policy_attachment.execution_managed]

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.name}-worker-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "worker"
      image     = "${var.ecr_repository_url}:latest"
      essential = true

      command = ["celery", "-A", "pokechaser", "worker", "-l", "INFO"]

      environment = local.common_environment
      secrets     = local.common_secrets

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecs_service" "worker" {
  name            = "${var.name}-worker-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [aws_iam_role_policy_attachment.execution_managed]

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecs_task_definition" "beat" {
  family                   = "${var.name}-beat-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "beat"
      image     = "${var.ecr_repository_url}:latest"
      essential = true

      command = ["celery", "-A", "pokechaser", "beat", "-l", "INFO"]

      environment = local.common_environment
      secrets     = local.common_secrets

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.beat.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Environment = var.environment
  }
}

resource "aws_ecs_service" "beat" {
  name            = "${var.name}-beat-${var.environment}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.beat.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [aws_security_group.tasks.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [aws_iam_role_policy_attachment.execution_managed]

  tags = {
    Environment = var.environment
  }
}
