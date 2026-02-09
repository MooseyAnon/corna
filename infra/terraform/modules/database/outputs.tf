# SAFE outputs
output "db_id" {
  value       = digitalocean_database_cluster.this.id
  description = "Managed DB cluster ID."
}

output "db_host" {
  value       = digitalocean_database_cluster.this.private_host
  description = "Private hostname inside the VPC."
}

output "db_port" {
  value       = digitalocean_database_cluster.this.port
  description = "DB port."
}

output "db_name" {
  value       = digitalocean_database_cluster.this.database
  description = "Default database name."
}

# SENSITIVE (won't print on console, still in state)
output "private_uri" {
  value       = digitalocean_database_cluster.this.private_uri
  sensitive   = true
  description = "Private connection URI (includes credentials) inside the VPC."
}

output "public_uri" {
  value       = digitalocean_database_cluster.this.uri
  sensitive   = true
  description = "Public connection URI (should be unused if relying on VPC + firewall)."
}

output "db_urn" {
  value       = digitalocean_database_cluster.this.urn
  description = "DB cluster URN for project attachments."
}
