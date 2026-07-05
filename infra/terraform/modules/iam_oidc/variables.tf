variable "name" {
  type = string
}

variable "environment" {
  type = string
}

variable "github_repo" {
  description = "GitHub repository in org/repo format (e.g. Thee-Dust/poke-chaser-django)"
  type        = string
}

variable "ecr_repository_arn" {
  type = string
}

variable "ecs_cluster_name" {
  description = "ECS cluster name — used to scope UpdateService to all services in the cluster"
  type        = string
}

variable "ecs_execution_role_arn" {
  type = string
}

variable "ecs_task_role_arn" {
  type = string
}
