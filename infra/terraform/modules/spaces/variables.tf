variable "bucket_name" {
  type        = string
  description = "Spaces bucket name."
}

variable "region" {
  type        = string
  description = "Spaces region code (e.g., lon, ams3, nyc3)."
  default     = "lon"
}

variable "project_name" {
  type        = string
  description = "Logical project name for naming context."
  default     = "corna"
}
