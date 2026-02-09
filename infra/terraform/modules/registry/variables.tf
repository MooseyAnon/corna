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
