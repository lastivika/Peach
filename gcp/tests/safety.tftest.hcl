# Fully mocked providers: these plans neither authenticate nor create resources.
mock_provider "google" {}
mock_provider "random" {}

variables {
  cognito_user_pool_id = "us-east-1_example"
  cognito_client_id    = "example-client"
}

run "foundation_has_no_workloads" {
  command = plan
  assert {
    condition     = length(google_cloud_run_v2_service.api) == 0 && length(google_cloud_run_v2_job.migrate) == 0
    error_message = "Bootstrap must not start an unmigrated API."
  }
  assert {
    condition     = length(google_sql_database_instance.main.settings[0].ip_configuration[0].authorized_networks) == 0
    error_message = "SQL must have no direct Internet allowlist."
  }
  assert {
    condition     = google_sql_database_instance.main.deletion_protection && google_sql_database_instance.main.settings[0].availability_type == "ZONAL"
    error_message = "Keep deletion protection and avoid paid HA for this lab."
  }
}

run "reject_api_without_migration_job" {
  command = plan
  variables {
    enable_api = true
    image      = "us-central1-docker.pkg.dev/peach-lab9-2026/peach/backend@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  expect_failures = [google_cloud_run_v2_service.api]
}

run "migrate_next_release_without_promoting_api" {
  command = plan
  variables {
    enable_api           = true
    enable_migration_job = true
    image                = "us-central1-docker.pkg.dev/peach-lab9-2026/peach/backend@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    migration_image      = "us-central1-docker.pkg.dev/peach-lab9-2026/peach/backend@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
  }
  assert {
    condition     = google_cloud_run_v2_service.api[0].template[0].containers[0].image == var.image && google_cloud_run_v2_job.migrate[0].template[0].template[0].containers[0].image == var.migration_image
    error_message = "Preparing a migration must not promote the live API."
  }
  assert {
    condition     = google_cloud_run_v2_job.migrate[0].template[0].template[0].max_retries == 0 && google_cloud_run_v2_job.migrate[0].template[0].parallelism == 1
    error_message = "Migration tasks must not retry or run concurrently."
  }
  assert {
    condition     = google_cloud_run_v2_service.api[0].template[0].scaling[0].min_instance_count == 0 && google_cloud_run_v2_service.api[0].template[0].scaling[0].max_instance_count == 1
    error_message = "Keep lab capacity bounded and allow scaling to zero."
  }
}
