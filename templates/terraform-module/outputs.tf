output "name_prefix" {
  description = "Resource নামের prefix: <project>-<environment>"
  value       = local.name_prefix
}

output "tags" {
  description = "সব resource-এ প্রয়োগযোগ্য common tag"
  value       = local.common_tags
}
