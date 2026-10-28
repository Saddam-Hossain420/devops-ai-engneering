# Template: reusable Terraform module structure
# এই উদাহরণ module কোনো cloud resource তৈরি করে না (খরচ নেই) —
# শুধু naming ও tagging convention তৈরি করে, যা অন্য module ব্যবহার করবে।

terraform {
  required_version = ">= 1.6"
}

locals {
  name_prefix = "${var.project}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project
      Environment = var.environment
      Owner       = var.owner
      ManagedBy   = "terraform"
    },
    var.extra_tags,
  )
}
