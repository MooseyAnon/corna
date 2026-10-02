output "droplet_id" { value = digitalocean_droplet.this.id }
output "droplet_ipv4" { value = digitalocean_droplet.this.ipv4_address }
output "droplet_name" { value = digitalocean_droplet.this.name }
output "admin_username" { value = var.admin_username }
output "droplet_urn" { value = digitalocean_droplet.this.urn }
