variable "registry_name" {
  type        = string
  description = "Name of the DO container registry."
}

variable "subscription_tier_slug" {
  type        = string
  description = "Registry tier (basic, professional, enterprise)."
  default     = "basic"
}

variable "project_name" {
  type        = string
  description = "Logical project name for tagging/naming help."
  default     = "corna"
}

variable "region" {
  type        = string
  description = "Registry region code (e.g., lon1, ams3, nyc3)."
  default     = "lon1"
}
