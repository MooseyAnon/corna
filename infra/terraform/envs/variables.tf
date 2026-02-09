# Setup
variable "project_name" {
  description = "Logical project name used in resource naming."
  type        = string
}

variable "project_description" {
  type    = string
  default = "Corna infrastructure (dev)"
}

variable "project_purpose" {
  type    = string
  default = "Web Application"
}

variable "project_environment" {
  type    = string
  default = "Development"
}

variable "region" {
  description = "DigitalOcean region (e.g., lon1, nyc3, ams3)."
  type        = string
  default     = "lon1"
}

# VPC
variable "enable_vpc" {
  description = "Enable the usage of a VPC."
  type        = bool
  default     = true
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

variable "vpc_description" {
  description = "VPC description."
  type        = string
  default     = "Project VPC"
}

# Compute inputs
variable "droplet_name"  {
  description = "The name of the droplet."
  type        = string 
  default     = "corna-host"
}

variable "droplet_size"  {
  description = "Size of the droplet."
  type        = string 
  default     = "s-1vcpu-2gb"
}

variable "droplet_image"  {
  description = "The image to use for the droplet."
  type        = string 
  default     = "rockylinux-9-x64"
}

variable "admin_username"  {
  description = "The username of the admin user."
  type        = string 
  default     = "admin"
}

variable "ssh_pub_key_path" {
  type    = string
  default = "~/.ssh/id_ed25519.pub"
}

variable "tags" {
  type    = list(string)
  default = ["corna","managed","public-edge"]
}

# Database
variable "enable_db" {
  type    = bool
  default = true
}

variable "db_engine" {
  type    = string
  default = "pg"
}

variable "db_version" {
  type    = string
  default = "16"
}

variable "db_size" {
  type    = string
  default = "db-s-1vcpu-1gb"
}

variable "db_name" {
  type    = string
  default = "corna-db"
}

variable "db_node_count" {
  type    = number
  default = 1
}

variable "db_allow_tag" {
  type    = string
  default = "corna"
}

variable "db_allow_cidrs" {
  type    = list(string)
  default = []
}

# Registry
variable "enable_registry" {
  type    = bool
  default = true
}

variable "registry_name" {
  type    = string
  default = "corna-registry"
}

variable "registry_tier" {
  type    = string
  default = "basic"
}

# S3
variable "enable_spaces" {
  type    = bool
  default = true
}

variable "spaces_bucket" {
  type    = string
  default = "corna-assets"
}

variable "spaces_region" {
  type    = string
  default = "lon"
}
