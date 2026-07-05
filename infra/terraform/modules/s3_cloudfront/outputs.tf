output "s3_bucket_name" {
  description = "S3 bucket that holds the built React assets"
  value       = aws_s3_bucket.frontend.id
}

output "s3_bucket_arn" {
  value = aws_s3_bucket.frontend.arn
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID — used for cache invalidations in CI"
  value       = aws_cloudfront_distribution.frontend.id
}

output "cloudfront_domain_name" {
  description = "CloudFront domain name (for verification before DNS propagates)"
  value       = aws_cloudfront_distribution.frontend.domain_name
}
