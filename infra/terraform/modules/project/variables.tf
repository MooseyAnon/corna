variable "project_name" {
  type        = string
  description = "DigitalOcean Project name."
}

variable "description" {
  type        = string
  description = "Project description."
  default     = "Corna infrastructure environment"
}

variable "purpose" {
  type        = string
  description = "Purpose shown in DO console (e.g., Web Application, Service/Monitoring, etc.)."
  default     = "Web Application"
}

variable "environment" {
  type        = string
  description = "Environment label (Development, Staging, Production)."
  default     = "Development"
}

variable "resource_urns" {
  type        = list(string)
  description = "URNs to attach to the Project. Can be empty; attachments will be skipped."
  default     = []
}
