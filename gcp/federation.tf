# Bootstrap locally using ADC in the SAME HCP workspace in Local execution mode.
# Switch to Remote only after this trust exists. No AWS state or credentials.
resource "google_service_account" "terraform" {
  count        = var.hcp_workspace_id == "" ? 0 : 1
  account_id   = "peach-terraform"
  display_name = "HCP peach-gcp-dev infrastructure manager"
  depends_on   = [google_project_service.api]
}
resource "google_iam_workload_identity_pool" "hcp" {
  count                     = var.hcp_workspace_id == "" ? 0 : 1
  workload_identity_pool_id = "peach-hcp"
  depends_on                = [google_project_service.api]
}
resource "google_iam_workload_identity_pool_provider" "hcp" {
  count                              = var.hcp_workspace_id == "" ? 0 : 1
  workload_identity_pool_id          = google_iam_workload_identity_pool.hcp[0].workload_identity_pool_id
  workload_identity_pool_provider_id = "hcp-terraform"
  attribute_mapping = {
    "google.subject"         = "assertion.sub"
    "attribute.workspace_id" = "assertion.terraform_workspace_id"
  }
  attribute_condition = "assertion.terraform_organization_name == 'peach-lab7' && assertion.terraform_workspace_name == 'peach-gcp-dev' && assertion.terraform_workspace_id == '${var.hcp_workspace_id}'"
  oidc { issuer_uri = "https://app.terraform.io" }
}
resource "google_service_account_iam_member" "hcp" {
  count              = var.hcp_workspace_id == "" ? 0 : 1
  service_account_id = google_service_account.terraform[0].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.hcp[0].name}/attribute.workspace_id/${var.hcp_workspace_id}"
}
# Infrastructure administration is intentionally separate from runtime identities.
# These project-scoped roles can alter IAM/secrets: restrict HCP apply and state access.
resource "google_project_iam_member" "terraform" {
  for_each = var.hcp_workspace_id == "" ? toset([]) : toset([
    "roles/serviceusage.serviceUsageAdmin", "roles/resourcemanager.projectIamAdmin",
    "roles/iam.serviceAccountAdmin", "roles/iam.serviceAccountUser",
    "roles/iam.workloadIdentityPoolAdmin", "roles/run.admin", "roles/cloudsql.admin",
    "roles/artifactregistry.admin", "roles/secretmanager.admin",
  ])
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.terraform[0].email}"
}
