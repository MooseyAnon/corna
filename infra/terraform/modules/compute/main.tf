terraform {
  required_version = ">= 1.5.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = ">= 2.40.0"
    }
  }
}

# 1) Import your SSH public key into DO
resource "digitalocean_ssh_key" "this" {
  name       = "${var.admin_username}-ssh"
  public_key = file(pathexpand(var.ssh_pub_key_path))
}

# 2) Droplet in the provided VPC
resource "digitalocean_droplet" "this" {
  name       = var.droplet_name
  region     = var.region
  size       = var.droplet_size
  image      = var.droplet_image
  vpc_uuid   = var.vpc_id

  ssh_keys   = [digitalocean_ssh_key.this.fingerprint]
  ipv6       = true
  monitoring = true
  tags       = distinct(concat(var.tags, ["public-edge"]))

  # Minimal cloud-init; Ansible will handle the rest
  user_data = templatefile(
    "${path.module}/cloud-init.yml",
    {
      admin_username = var.admin_username
      ssh_public_key = trimspace(
        file(pathexpand(var.ssh_pub_key_path))
      )
    }
  )
}

# 3) Tag-based Cloud Firewall at DO edge
resource "digitalocean_firewall" "edge" {
  name = "${var.project_name}-fw"
  tags = ["public-edge"]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }
  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}
