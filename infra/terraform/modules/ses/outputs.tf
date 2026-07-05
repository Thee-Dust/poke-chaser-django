output "smtp_username" {
  description = "SES SMTP username (IAM access key ID) — maps to EMAIL_HOST_USER"
  value       = aws_iam_access_key.smtp.id
}

output "smtp_password" {
  description = "SES SMTP password (derived from IAM secret key) — maps to EMAIL_HOST_PASSWORD"
  value       = aws_iam_access_key.smtp.ses_smtp_password_v4
  sensitive   = true
}

output "identity_arn" {
  value = aws_ses_domain_identity.main.arn
}
