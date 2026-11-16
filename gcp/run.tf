resource "google_cloud_run_v2_job" "migrate" {
  count               = var.enable_migration_job ? 1 : 0
  name                = "peach-migrate"
  location            = var.region
  deletion_protection = var.deletion_protection
  template {
    task_count  = 1
    parallelism = 1
    template {
      service_account = google_service_account.workload["migrate"].email
      max_retries     = 0
      timeout         = "600s"
      volumes {
        name = "cloudsql"
        cloud_sql_instance { instances = [google_sql_database_instance.main.connection_name] }
      }
      containers {
        image   = var.migration_image != "" ? var.migration_image : var.image
        command = ["alembic"]
        args    = ["upgrade", "head"]
        resources { limits = { cpu = "1", memory = "512Mi" } }
        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
        env {
          name = "DATABASE_URL"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.database.secret_id
              version = google_secret_manager_secret_version.database.version
            }
          }
        }
        dynamic "env" {
          for_each = local.environment
          content {
            name  = env.key
            value = env.value
          }
        }
      }
    }
  }
  lifecycle {
    precondition {
      condition     = var.image != "" || var.migration_image != ""
      error_message = "Publish an image and configure its digest before enabling migrations."
    }
  }
  depends_on = [google_secret_manager_secret_iam_member.database, google_project_iam_member.sql_client]
}
resource "google_cloud_run_v2_service" "api" {
  count               = var.enable_api ? 1 : 0
  name                = "peach-api"
  location            = var.region
  deletion_protection = var.deletion_protection
  ingress             = "INGRESS_TRAFFIC_ALL"
  template {
    service_account                  = google_service_account.workload["api"].email
    execution_environment            = "EXECUTION_ENVIRONMENT_GEN2"
    max_instance_request_concurrency = 8
    timeout                          = "60s"
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }
    volumes {
      name = "cloudsql"
      cloud_sql_instance { instances = [google_sql_database_instance.main.connection_name] }
    }
    containers {
      image = var.image
      ports { container_port = 8080 }
      resources {
        limits   = { cpu = "1", memory = "512Mi" }
        cpu_idle = true
      }
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }
      startup_probe {
        http_get { path = "/health" }
        initial_delay_seconds = 0
        period_seconds        = 5
        failure_threshold     = 12
      }
      liveness_probe {
        http_get { path = "/health" }
        period_seconds = 30
      }
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database.secret_id
            version = google_secret_manager_secret_version.database.version
          }
        }
      }
      dynamic "env" {
        for_each = local.environment
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }
  lifecycle {
    precondition {
      condition     = var.image != "" && var.enable_migration_job && var.cognito_user_pool_id != "" && var.cognito_client_id != ""
      error_message = "API requires an image, migration job and Cognito configuration. Execute migrations before enabling API."
    }
  }
  depends_on = [google_secret_manager_secret_iam_member.database, google_project_iam_member.sql_client]
}
# Browser sends Cognito ID tokens, not Google IAM tokens. FastAPI retains JWT
# verification and owner checks on every data endpoint. CORS is not authorization.
resource "google_cloud_run_v2_service_iam_member" "browser" {
  count    = var.enable_api ? 1 : 0
  location = var.region
  name     = google_cloud_run_v2_service.api[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
