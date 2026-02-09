variable "project_name"     { type = string }
variable "region"           { type = string }
variable "vpc_id"           { type = string }

variable "droplet_name"     { type = string }
variable "droplet_size"     { type = string }
variable "droplet_image"    { type = string }
variable "admin_username"   { type = string }
variable "ssh_pub_key_path" { type = string }
variable "tags"             {
  type    = list(string)
  default = []
}
