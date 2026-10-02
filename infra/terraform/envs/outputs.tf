output "project_id" {
  value       = module.project.project_id
  description = "DigitalOcean Project ID (dev)."
}

output "vpc_id" { value = module.network.vpc_id }
output "droplet_ipv4" { value = module.compute.droplet_ipv4 }
output "droplet_user" { value = module.compute.admin_username }

# SAFE DB outputs
output "db_host" { value = try(module.database[0].db_host, null) }
output "db_port" { value = try(module.database[0].db_port, null) }
output "db_name" { value = try(module.database[0].db_name, null) }

# SENSITIVE DB outputs (won't print to console)
output "db_private_uri" {
  value     = try(module.database[0].private_uri, null)
  sensitive = true
}
output "db_public_uri" {
  value     = try(module.database[0].public_uri, null)
  sensitive = true
}

# Registry outputs (exist only if enabled)
output "registry_name" {
  value       = try(module.registry[0].name, null)
  description = "Container registry name (if enabled)."
}

output "registry_endpoint" {
  value       = try(module.registry[0].endpoint, null)
  description = "Container registry endpoint (if enabled)."
}

# Spaces outputs (exist only if enabled)
output "spaces_bucket" {
  value       = try(module.spaces[0].name, null)
  description = "Spaces bucket name (if enabled)."
}

output "spaces_region" {
  value       = try(module.spaces[0].region, null)
  description = "Spaces region (if enabled)."
}

output "spaces_endpoint" {
  value       = try(module.spaces[0].endpoint, null)
  description = "S3 endpoint (if enabled)."
}

