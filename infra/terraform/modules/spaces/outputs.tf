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
