output "name" {
  description = "Registry name."
  value       = digitalocean_container_registry.this.name
}

output "endpoint" {
  description = "Docker endpoint for the registry."
  value       = digitalocean_container_registry.this.server_url
}
