locals {
  apis = toset([
    "serviceusage.googleapis.com", "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com", "iamcredentials.googleapis.com", "sts.googleapis.com",
    "run.googleapis.com", "sqladmin.googleapis.com", "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com", "firebase.googleapis.com", "firebasehosting.googleapis.com",
  ])
  environment = {
    APP_ENV              = "production"
    DB_POOLING           = "false"
    COGNITO_REGION       = var.cognito_region
    COGNITO_USER_POOL_ID = var.cognito_user_pool_id
    COGNITO_CLIENT_ID    = var.cognito_client_id
    CORS_ORIGINS         = "https://${var.project_id}.web.app,https://${var.project_id}.firebaseapp.com"
  }
}
resource "google_project_service" "api" {
  for_each           = local.apis
  service            = each.value
  disable_on_destroy = false
}
resource "google_artifact_registry_repository" "backend" {
  location      = var.region
  repository_id = "peach"
  format        = "DOCKER"
  depends_on    = [google_project_service.api]
}
resource "google_service_account" "workload" {
  for_each     = toset(["api", "migrate"])
  account_id   = "peach-${each.key}"
  display_name = "Peach ${each.key} (no service account keys)"
  depends_on   = [google_project_service.api]
}
resource "google_project_iam_member" "sql_client" {
  for_each = google_service_account.workload
  project  = var.project_id
  role     = "roles/cloudsql.client"
  member   = "serviceAccount:${each.value.email}"
}
resource "google_sql_database_instance" "main" {
  name                = "peach-postgres"
  region              = var.region
  database_version    = "POSTGRES_16"
  deletion_protection = var.deletion_protection
  settings {
    tier                        = "db-f1-micro"
    edition                     = "ENTERPRISE"
    availability_type           = "ZONAL"
    disk_type                   = "PD_SSD"
    disk_size                   = 10
    disk_autoresize             = false
    deletion_protection_enabled = var.deletion_protection
    ip_configuration {
      # Cloud Run's authenticated Cloud SQL proxy uses public IP. No authorized
      # networks: direct connections from the Internet are not allowed.
      ipv4_enabled = true
      ssl_mode     = "ENCRYPTED_ONLY"
    }
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = false
      start_time                     = "03:00"
      backup_retention_settings { retained_backups = 2 }
    }
  }
  depends_on = [google_project_service.api]
}
resource "google_sql_database" "peach" {
  name      = "peach"
  instance  = google_sql_database_instance.main.name
  charset   = "UTF8"
  collation = "en_US.UTF8"
}
resource "random_password" "database" {
  length  = 40
  special = false
}
resource "google_sql_user" "peach" {
  name     = "peach"
  instance = google_sql_database_instance.main.name
  password = random_password.database.result
}
resource "google_secret_manager_secret" "database" {
  secret_id = "peach-database-url"
  replication {
    auto {}
  }
  depends_on = [google_project_service.api]
}
# This value IS present in state. Limit HCP state access as tightly as secrets.
resource "google_secret_manager_secret_version" "database" {
  secret      = google_secret_manager_secret.database.id
  secret_data = "postgresql+asyncpg://peach:${random_password.database.result}@/peach?host=/cloudsql/${google_sql_database_instance.main.connection_name}"
  depends_on  = [google_sql_user.peach, google_sql_database.peach]
}
resource "google_secret_manager_secret_iam_member" "database" {
  for_each  = google_service_account.workload
  secret_id = google_secret_manager_secret.database.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value.email}"
}
