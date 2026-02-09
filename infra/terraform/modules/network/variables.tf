variable "project_name" {
  description = "Logical project name used in resource naming."
  type        = string
}

variable "region" {
  description = "DigitalOcean region (e.g., lon1, nyc3, ams3)."
  type        = string
  default     = "lon1"
}

variable "create_vpc" {
  description = "Whether to create a new VPC. If false, you must supply existing_vpc_id."
  type        = bool
  default     = true
}

variable "existing_vpc_id" {
  description = "Existing VPC ID to reuse when create_vpc=false."
  type        = string
  default     = ""
}

variable "existing_vpc_name" {
  description = "Optional: name of the existing VPC (for outputs/docs only)."
  type        = string
  default     = ""
}

variable "vpc_name" {
  description = "Optional explicit VPC name. Defaults to <project_name>-vpc."
  type        = string
  default     = ""
}

variable "vpc_cidr" {
  description = "RFC1918 CIDR for the VPC (e.g., 10.20.0.0/16)."
  type        = string
  default     = "10.20.0.0/16"
  validation {
    condition     = can(cidrnetmask(var.vpc_cidr))
    error_message = "vpc_cidr must be a valid CIDR."
  }
}

variable "description" {
  description = "VPC description."
  type        = string
  default     = "Project VPC"
}

# Guardrails
locals {
  _validation_ok = (
    var.create_vpc || (trimspace(var.existing_vpc_id) != "")
  )
}

# Fails early if neither creating nor providing an existing VPC ID
resource "null_resource" "validate" {
  triggers = {
    ok = tostring(local._validation_ok)
  }
  lifecycle {
    precondition {
      condition     = local._validation_ok
      error_message = "create_vpc=false requires existing_vpc_id to be set."
    }
  }
}
