variable "project" {
  description = "Project-এর ছোট নাম (lowercase, hyphen)"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,30}$", var.project))
    error_message = "project: lowercase অক্ষর, সংখ্যা ও hyphen, ২–৩১ অক্ষর।"
  }
}

variable "environment" {
  description = "dev, staging বা prod"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment হতে হবে dev, staging বা prod।"
  }
}

variable "owner" {
  description = "দায়িত্বপ্রাপ্ত ব্যক্তি/team (cost allocation-এর জন্য)"
  type        = string
}

variable "extra_tags" {
  description = "অতিরিক্ত tag"
  type        = map(string)
  default     = {}
}
