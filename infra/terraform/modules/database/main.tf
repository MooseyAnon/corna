terraform {
  required_version = ">= 1.5.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = ">= 2.40.0"
    }
  }
}

# 1) Managed DB cluster
resource "digitalocean_database_cluster" "this" {
  name                  = var.name
  engine                = var.engine
  version               = var.engine_version
  size                  = var.size
  region                = var.region
  node_count            = var.node_count
  private_network_uuid  = var.vpc_id
  tags                  = var.tags
}

# 2) Database firewall: trust only droplets with allow_tag, plus optional CIDRs.
#    (No public 0.0.0.0/0 here.)
resource "digitalocean_database_firewall" "this" {
  cluster_id = digitalocean_database_cluster.this.id

  # Allow by tag (recommended for your app droplets)
  rule {
    type  = "tag"
    value = var.allow_tag
  }

  # Optional static CIDRs (e.g., your CI runner).
  dynamic "rule" {
    for_each = var.allow_cidrs
    content {
      type  = "ip_addr"
      value = rule.value
    }
  }
}
