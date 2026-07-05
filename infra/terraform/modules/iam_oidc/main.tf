data "aws_caller_identity" "current" {}

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
  ]
}

resource "aws_iam_role" "github_deploy" {
  name = "${var.name}-github-deploy-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:ref:refs/tags/*"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy" {
  name = "${var.name}-github-deploy-${var.environment}"
  role = aws_iam_role.github_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECRLogin"
        Effect = "Allow"
        Action = ["ecr:GetAuthorizationToken"]
        Resource = ["*"]
      },
      {
        Sid    = "ECRPush"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage"
        ]
        Resource = [var.ecr_repository_arn]
      },
      {
        Sid    = "ECSDescribe"
        Effect = "Allow"
        Action = [
          "ecs:DescribeClusters",
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:DescribeTasks",
          "ecs:ListTasks"
        ]
        Resource = ["*"]
      },
      {
        Sid    = "ECSUpdateService"
        Effect = "Allow"
        Action = ["ecs:UpdateService"]
        Resource = ["arn:aws:ecs:*:${data.aws_caller_identity.current.account_id}:service/${var.ecs_cluster_name}/*"]
      },
      {
        Sid    = "ECSRunTask"
        Effect = "Allow"
        Action = ["ecs:RunTask"]
        Resource = ["arn:aws:ecs:*:${data.aws_caller_identity.current.account_id}:task-definition/${var.name}-*-${var.environment}:*"]
      },
      {
        Sid    = "ECSRegisterTaskDef"
        Effect = "Allow"
        Action = ["ecs:RegisterTaskDefinition"]
        Resource = ["*"]
      },
      {
        Sid    = "PassRole"
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          var.ecs_execution_role_arn,
          var.ecs_task_role_arn
        ]
      }
    ]
  })
}
