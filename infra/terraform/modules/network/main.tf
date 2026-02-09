terraform {
  required_version = ">= 1.5.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = ">= 2.40.0"
    }
  }
}

# If create_vpc = true, we create a VPC.
# If create_vpc = false, we require existing_vpc_id to be provided and just pass it through.

# Create-only path
resource "digitalocean_vpc" "this" {
  count      = var.create_vpc ? 1 : 0
  name       = var.vpc_name != "" ? var.vpc_name : "${var.project_name}-vpc"
  region     = var.region
  ip_range   = var.vpc_cidr
  description = var.description
}

locals {
  effective_vpc_id   = var.create_vpc ? digitalocean_vpc.this[0].id : var.existing_vpc_id
  effective_vpc_name = var.create_vpc ? digitalocean_vpc.this[0].name : var.existing_vpc_name
  effective_region   = var.region
  effective_cidr     = var.vpc_cidr
}
