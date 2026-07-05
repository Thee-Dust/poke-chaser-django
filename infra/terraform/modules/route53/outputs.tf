output "zone_id" {
  value = aws_route53_zone.main.zone_id
}

output "name_servers" {
  description = "Set these at your domain registrar BEFORE running the full terraform apply"
  value       = aws_route53_zone.main.name_servers
}
