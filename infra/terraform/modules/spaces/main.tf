terraform {
  required_version = ">= 1.5.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = ">= 2.40.0"
    }
  }
}

resource "digitalocean_spaces_bucket" "this" {
  name   = var.bucket_name
  region = var.region
  acl    = "private"
}
