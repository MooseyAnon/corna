variable "project_name" {
  type        = string
  description = "Project name for tagging/naming."
}

variable "region" {
  type        = string
  description = "DO region for the DB (e.g., lon1)."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for private networking."
}

variable "engine" {
  type        = string
  description = "Database engine: pg, mysql, or redis."
  default     = "pg"
}

variable "engine_version" {
  type        = string
  description = "Engine version (e.g., 16 for Postgres)."
  default     = "16"
}

variable "size" {
  type        = string
  description = "DO managed DB size slug."
  default     = "db-s-1vcpu-1gb"
}

variable "name" {
  type        = string
  description = "Cluster name."
  default     = "corna-db"
}

variable "node_count" {
  type        = number
  description = "Number of nodes in the cluster."
  default     = 1
}

variable "tags" {
  type        = list(string)
  description = "Tags to add to the cluster."
  default     = []
}

variable "allow_tag" {
  type        = string
  description = "Droplet tag allowed to connect (DB firewall)."
  default     = "corna"
}

variable "allow_cidrs" {
  type        = list(string)
  description = "Optional list of CIDR IPs allowed to connect (DB firewall). Avoid using unless needed."
  default     = []
}
