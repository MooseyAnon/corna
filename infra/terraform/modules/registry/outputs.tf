output "name" {
  description = "Registry name."
  value       = digitalocean_container_registry.this.name
}

output "endpoint" {
  description = "Docker endpoint for the registry."
  value       = digitalocean_container_registry.this.server_url
}

# registries cannot be attached to VPC's and projects, so this will probably not
# get used in prod.
# Eitherway, this is made up and only useful for logging purposes
output "urn" {
  description = "Container registry URN for project attachments."
  value       = "do:registry:${digitalocean_container_registry.this.name}"
}
