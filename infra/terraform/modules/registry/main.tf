terraform {
  required_version = ">= 1.5.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = ">= 2.40.0"
    }
  }
}

resource "digitalocean_container_registry" "this" {
  name                   = var.registry_name
  subscription_tier_slug = var.subscription_tier_slug
}
