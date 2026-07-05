resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.name}-${var.environment}"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "${var.name}-redis-subnet-group"
    Environment = var.environment
  }
}

resource "aws_security_group" "redis" {
  name        = "${var.name}-redis-${var.environment}"
  description = "Allow Redis from ECS tasks"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = var.allowed_security_group_ids
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.name}-redis-sg"
    Environment = var.environment
  }
}

resource "aws_elasticache_cluster" "main" {
  cluster_id           = "${var.name}-${var.environment}"
  engine               = "redis"
  node_type            = var.node_type
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  tags = {
    Name        = "${var.name}-redis"
    Environment = var.environment
  }
}
