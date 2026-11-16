output "api_url" { value = try(google_cloud_run_v2_service.api[0].uri, null) }
output "image_repository" { value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.backend.repository_id}/backend" }
output "sql_connection_name" { value = google_sql_database_instance.main.connection_name }
output "site_url" { value = "https://${var.project_id}.web.app" }
output "hcp_workload_provider" { value = try(google_iam_workload_identity_pool_provider.hcp[0].name, null) }
output "hcp_service_account" { value = try(google_service_account.terraform[0].email, null) }
