output "vpc_id" {
  description = "The VPC ID used by downstream modules."
  value       = local.effective_vpc_id
}

output "vpc_name" {
  description = "Name of the VPC (created or existing)."
  value       = local.effective_vpc_name
}

output "vpc_region" {
  description = "Region of the VPC."
  value       = local.effective_region
}

output "vpc_cidr" {
  description = "CIDR of the VPC."
  value       = local.effective_cidr
}

output "created" {
  description = "True if this module created the VPC."
  value       = var.create_vpc
}
