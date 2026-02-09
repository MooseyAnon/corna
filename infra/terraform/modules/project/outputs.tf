output "project_id" {
  description = "ID of the created Project."
  value       = digitalocean_project.this.id
}

output "project_name" {
  description = "Name of the created Project."
  value       = digitalocean_project.this.name
}
