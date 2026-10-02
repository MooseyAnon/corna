# --- Network (your module from previous step)
module "network" {
  source       = "../modules/network"
  project_name = var.project_name
  region       = var.region
  create_vpc   = var.enable_vpc
  vpc_cidr     = var.vpc_cidr
  description  = var.vpc_description
}

# --- Compute (new module)
module "compute" {
  source           = "../modules/compute"
  project_name     = var.project_name
  region           = var.region
  vpc_id           = module.network.vpc_id
  droplet_name     = var.droplet_name
  droplet_size     = var.droplet_size
  droplet_image    = var.droplet_image
  admin_username   = var.admin_username
  ssh_pub_key_path = var.ssh_pub_key_path
  tags             = var.tags
}

# --- Database (Managed Postgres with VPC + firewall)
module "database" {
  source       = "../modules/database"
  count        = var.enable_db ? 1 : 0
  project_name = var.project_name
  region       = var.region
  vpc_id       = module.network.vpc_id

  engine         = var.db_engine
  engine_version = var.db_version
  size           = var.db_size
  name           = var.db_name
  node_count     = var.db_node_count
  tags           = var.tags

  allow_tag   = var.db_allow_tag
  allow_cidrs = var.db_allow_cidrs
}

moved {
  from = module.database
  to   = module.database[0]
}

# --- Registry (optional)
module "registry" {
  source                 = "../modules/registry"
  count                  = var.enable_registry ? 1 : 0
  project_name           = var.project_name
  registry_name          = var.registry_name
  subscription_tier_slug = var.registry_tier
  region                 = var.registry_region
}

# --- Spaces (optional)
module "spaces" {
  source       = "../modules/spaces"
  count        = var.enable_spaces ? 1 : 0
  project_name = var.project_name
  bucket_name  = var.spaces_bucket
  region       = var.spaces_region
}

# --- Project + Attachments
# Build the list of resource URNs (filter out nulls for optional modules)
locals {
  project_resource_urns = tolist([
    for r in [
      module.compute.droplet_urn,
      try(module.database[0].db_urn, null),
      try(module.spaces[0].urn, null)
    ] : r if r != null
  ])
}

module "project" {
  source        = "../modules/project"
  project_name  = var.project_name
  description   = var.project_description
  purpose       = var.project_purpose
  environment   = var.project_environment
  resource_urns = local.project_resource_urns
}
