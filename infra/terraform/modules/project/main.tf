terraform {
  required_version = ">= 1.5.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = ">= 2.40.0"
    }
  }
}

resource "digitalocean_project" "this" {
  name        = var.project_name
  description = var.description
  purpose     = var.purpose
  environment = var.environment
}

# Only create the attachment resource if we actually have something to attach.
resource "digitalocean_project_resources" "attachments" {
  # count    = length(var.resource_urns) > 0 ? 1 : 0
  project  = digitalocean_project.this.id
  resources = var.resource_urns
}
