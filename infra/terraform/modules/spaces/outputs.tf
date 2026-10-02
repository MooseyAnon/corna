output "name" {
  description = "Spaces bucket name."
  value       = digitalocean_spaces_bucket.this.name
}

output "region" {
  description = "Spaces region code."
  value       = digitalocean_spaces_bucket.this.region
}

output "endpoint" {
  description = "S3-compatible endpoint URL for this region."
  value       = "https://${digitalocean_spaces_bucket.this.region}.digitaloceanspaces.com"
}

output "urn" {
  description = "Spaces bucket URN for project attachments."
  value       = digitalocean_spaces_bucket.this.urn
}

output "spaces_access_key" {
  description = "Spaces bucket access key used by application processes."
  value       = digitalocean_spaces_key.this.access_key
  sensitive   = true
}

output "spaces_secret_key" {
  description = "Spaces bucket secret token used by application processes."
  value       = digitalocean_spaces_key.this.secret_key
  sensitive   = true
}
