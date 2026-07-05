output "role_arn" {
  description = "Set this as AWS_DEPLOY_ROLE_ARN in GitHub Actions repository variables"
  value       = aws_iam_role.github_deploy.arn
}

output "oidc_provider_arn" {
  value = aws_iam_openid_connect_provider.github.arn
}
