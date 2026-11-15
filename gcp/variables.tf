variable "project_id" {
  type    = string
  default = "peach-lab9-2026"
  validation {
    condition     = var.project_id == "peach-lab9-2026"
    error_message = "This lab root is restricted to peach-lab9-2026."
  }
}
variable "region" {
  type    = string
  default = "us-central1"
  validation {
    condition     = var.region == "us-central1"
    error_message = "The lab image and runbook are scoped to us-central1."
  }
}
variable "cognito_region" {
  type    = string
  default = "us-east-1"
}
variable "cognito_user_pool_id" { type = string }
variable "cognito_client_id" { type = string }
variable "image" {
  description = "Published linux/amd64 backend image pinned by sha256 digest. Empty during bootstrap."
  type        = string
  default     = ""
  validation {
    condition     = var.image == "" || can(regex("^us-central1-docker.pkg.dev/peach-lab9-2026/peach/backend@sha256:[a-f0-9]{64}$", var.image))
    error_message = "Use the immutable backend digest from this project's Artifact Registry."
  }
}
variable "enable_migration_job" {
  type    = bool
  default = false
}
variable "enable_api" {
  description = "Enable only after the migration job succeeds."
  type        = bool
  default     = false
}
variable "deletion_protection" {
  type    = bool
  default = true
}
variable "hcp_workspace_id" {
  description = "Immutable ws-... ID of peach-gcp-dev. Empty disables federation until bootstrap is configured."
  type        = string
  default     = ""
}

variable "migration_image" {
  description = "Optional next-release digest for migrating before promoting the API image. Empty uses image."
  type        = string
  default     = ""
  validation {
    condition     = var.migration_image == "" || can(regex("^us-central1-docker.pkg.dev/peach-lab9-2026/peach/backend@sha256:[a-f0-9]{64}$", var.migration_image))
    error_message = "Use an immutable backend digest from this project's Artifact Registry."
  }
}
