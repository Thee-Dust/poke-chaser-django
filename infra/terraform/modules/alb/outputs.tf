output "alb_arn" {
  value = aws_lb.main.arn
}

output "alb_dns_name" {
  value = aws_lb.main.dns_name
}

output "alb_zone_id" {
  value = aws_lb.main.zone_id
}

output "target_group_arn" {
  value = aws_lb_target_group.api.arn
}

output "security_group_id" {
  description = "ALB security group — ECS tasks allow ingress from this"
  value       = aws_security_group.alb.id
}

output "certificate_arn" {
  value = aws_acm_certificate_validation.api.certificate_arn
}
