# GCP Terraform plan review — 2026-11-12

> Deployment update: recovery completed on 2026-11-14; all 37 resources are
> managed and the consistency plan reports no changes.
> See [LAB9-DEPLOYMENT.md](LAB9-DEPLOYMENT.md). The original plan must not be reused.

## Pre-apply refresh — 2026-11-14

Refreshed saved plan: **37 create, 0 change, 0 destroy**. All resource addresses
and previously allowlisted review fields match the prior plan. Init, fmt check
and validate passed. HCP authenticated checks confirm GCP workspace
`ws-V2VUazTYGTjPNfgS`, Local execution, auto-apply disabled, working directory
`gcp`; AWS workspace remains separate (`ws-Z7CeegiCjc7giCYq`).

The saved binary is protected in a private temporary directory; its path and
SHA-256 are recorded in ignored `submission/lab9/pending-apply.json`. Approval
is pending. No apply or cloud resource creation has occurred.

ADC token refresh works. Regular gcloud user authentication now requires
`gcloud auth login`. A fresh ADC project metadata lookup was blocked because
Cloud Resource Manager API is disabled; enabling that API is already included
in the reviewed foundation plan. Project lifecycle/number were not reverified
by that lookup. All planned project fields still target `peach-lab9-2026`.

Cloud SQL pricing rechecked: approximately $9.37/month for compute and 10 GiB
SSD, plus backups, other usage and tax. The $5 alert is not a cap.

After bootstrap, validate HCP WIF authentication before changing execution mode
to Remote, as requested. The older sequence below is superseded by this gate.
No WIF authentication success is claimed before the trust is deployed and tested.

## Verified result

**37 to create, 0 to change, 0 to destroy; no replacements.** This is an actual
ADC-authenticated local Terraform plan using the dedicated HCP GCP workspace,
not a mocked test. Exit code 2 indicates a successful plan with proposed changes.
No apply or destroy was run. Planned resources do not yet exist merely because
planning succeeded.

| Workspace           | Immutable ID          | Execution | Auto-apply | Directory | Terraform |
| ------------------- | --------------------- | --------- | ---------- | --------- | --------- |
| GCP `peach-gcp-dev` | `ws-V2VUazTYGTjPNfgS` | Local     | Disabled   | `gcp`     | 1.13.5    |
| AWS `peach-dev`     | `ws-Z7CeegiCjc7giCYq` | Remote    | Enabled    | `infra`   | 1.17.1    |

The new GCP workspace initially had Remote execution, an empty working directory
and Terraform 1.17.2. Only its execution mode, directory and version were changed
to the verified local bootstrap settings above; auto-apply remained disabled.
AWS workspace settings were not changed. The ignored `gcp/terraform.tfvars` now
contains the GCP immutable workspace ID. Both workload enable flags remain false.

`init -input=false`, recursive formatting/check, provider schema validation and
`plan -input=false -detailed-exitcode` completed successfully. Providers are locked
to Google 7.46.2 and Random 3.9.1. State stays in `peach-lab7/peach-gcp-dev`; there
is no AWS provider, remote-state reference or AWS resource action in this plan.
Every Google resource with a planned project points to `peach-lab9-2026`.

The temporary binary plan and verbose plan log were deleted after extracting
allowlisted, non-secret review fields. The sanitized snapshot is in ignored
`submission/lab9/plan-summary.json`. No password, token, secret payload or state
contents were printed. Re-run a fresh plan before any future deployment approval.

## Every planned resource address

All addresses below have action **create**. API entries enable/manage API state;
they do not create duplicate services when an API was already enabled.

| Address                                                                        | Intended object / permission                                                         |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| `google_artifact_registry_repository.backend`                                  | Docker repository `peach`, us-central1                                               |
| `google_iam_workload_identity_pool.hcp[0]`                                     | Workload identity pool `peach-hcp`                                                   |
| `google_iam_workload_identity_pool_provider.hcp[0]`                            | OIDC provider `hcp-terraform`, issuer app.terraform.io                               |
| `google_project_iam_member.sql_client["api"]`                                  | `roles/cloudsql.client` for the named workload account                               |
| `google_project_iam_member.sql_client["migrate"]`                              | `roles/cloudsql.client` for the named workload account                               |
| `google_project_iam_member.terraform["roles/artifactregistry.admin"]`          | `roles/artifactregistry.admin` for the Terraform account                             |
| `google_project_iam_member.terraform["roles/cloudsql.admin"]`                  | `roles/cloudsql.admin` for the Terraform account                                     |
| `google_project_iam_member.terraform["roles/iam.serviceAccountAdmin"]`         | `roles/iam.serviceAccountAdmin` for the Terraform account                            |
| `google_project_iam_member.terraform["roles/iam.serviceAccountUser"]`          | `roles/iam.serviceAccountUser` for the Terraform account                             |
| `google_project_iam_member.terraform["roles/iam.workloadIdentityPoolAdmin"]`   | `roles/iam.workloadIdentityPoolAdmin` for the Terraform account                      |
| `google_project_iam_member.terraform["roles/resourcemanager.projectIamAdmin"]` | `roles/resourcemanager.projectIamAdmin` for the Terraform account                    |
| `google_project_iam_member.terraform["roles/run.admin"]`                       | `roles/run.admin` for the Terraform account                                          |
| `google_project_iam_member.terraform["roles/secretmanager.admin"]`             | `roles/secretmanager.admin` for the Terraform account                                |
| `google_project_iam_member.terraform["roles/serviceusage.serviceUsageAdmin"]`  | `roles/serviceusage.serviceUsageAdmin` for the Terraform account                     |
| `google_project_service.api["artifactregistry.googleapis.com"]`                | API `artifactregistry.googleapis.com`                                                |
| `google_project_service.api["cloudresourcemanager.googleapis.com"]`            | API `cloudresourcemanager.googleapis.com`                                            |
| `google_project_service.api["firebase.googleapis.com"]`                        | API `firebase.googleapis.com`                                                        |
| `google_project_service.api["firebasehosting.googleapis.com"]`                 | API `firebasehosting.googleapis.com`                                                 |
| `google_project_service.api["iam.googleapis.com"]`                             | API `iam.googleapis.com`                                                             |
| `google_project_service.api["iamcredentials.googleapis.com"]`                  | API `iamcredentials.googleapis.com`                                                  |
| `google_project_service.api["run.googleapis.com"]`                             | API `run.googleapis.com`                                                             |
| `google_project_service.api["secretmanager.googleapis.com"]`                   | API `secretmanager.googleapis.com`                                                   |
| `google_project_service.api["serviceusage.googleapis.com"]`                    | API `serviceusage.googleapis.com`                                                    |
| `google_project_service.api["sqladmin.googleapis.com"]`                        | API `sqladmin.googleapis.com`                                                        |
| `google_project_service.api["sts.googleapis.com"]`                             | API `sts.googleapis.com`                                                             |
| `google_secret_manager_secret.database`                                        | Secret `peach-database-url`                                                          |
| `google_secret_manager_secret_iam_member.database["api"]`                      | Secret Accessor on this secret only for the named workload account                   |
| `google_secret_manager_secret_iam_member.database["migrate"]`                  | Secret Accessor on this secret only for the named workload account                   |
| `google_secret_manager_secret_version.database`                                | Version containing the generated DB connection URL (sensitive)                       |
| `google_service_account.terraform[0]`                                          | Service account `peach-terraform`                                                    |
| `google_service_account.workload["api"]`                                       | Service account `peach-api`                                                          |
| `google_service_account.workload["migrate"]`                                   | Service account `peach-migrate`                                                      |
| `google_service_account_iam_member.hcp[0]`                                     | Workload Identity User on peach-terraform, restricted to the GCP workspace principal |
| `google_sql_database.peach`                                                    | Database `peach`, UTF8, en_US.UTF8                                                   |
| `google_sql_database_instance.main`                                            | Instance `peach-postgres`, PostgreSQL 16, db-f1-micro, 10 GiB SSD                    |
| `google_sql_user.peach`                                                        | Database user `peach`                                                                |
| `random_password.database`                                                     | 40-character generated database password (sensitive)                                 |

Count reconciliation: 11 API resources + 1 repository + 3 service accounts +
11 project IAM grants (2 runtime SQL-client, 9 Terraform administration) +
3 WIF resources (pool, provider, service-account binding) + 3 SQL resources
(instance/database/user) + 1 password + 4 secret resources (secret/version/2 grants)
= **37**.

No Cloud Run service, migration job or public invoker binding is planned yet.
No VPC connector, NAT, load balancer, HA database or GPU is defined. Firebase
project registration and Hosting deployment are not created by this plan.

## Security and permissions review

- SQL public IPv4 is enabled, but the authorized-network list is empty and
  `ssl_mode=ENCRYPTED_ONLY`. The intended connection is Cloud Run's authenticated
  Cloud SQL proxy, not an unrestricted Internet database port.
- API and migration accounts each get only project Cloud SQL client plus access
  to the one DB secret. They remain distinct from the infrastructure administrator.
- The Terraform account receives nine administration roles, including Project IAM
  Admin, Secret Manager Admin and Service Account User. These are powerful
  project-level grants, needed by the current monolithic root to manage IAM,
  secrets and workloads. Keep HCP membership, trusted code and state access tightly
  restricted; this is not a narrowly scoped runtime identity. No Owner/Editor role
  or service-account key is planned.
- The WIF issuer is `https://app.terraform.io`. Trust requires organization
  `peach-lab7`, workspace `peach-gcp-dev`, and immutable ID
  `ws-V2VUazTYGTjPNfgS`; its service-account binding uses that workspace attribute.
  The current trust permits both plan/apply runs of that workspace. Splitting
  read-only plan and write-capable apply identities would tighten a production setup.
- DB password and secret payload will be stored in Terraform state. Sensitive
  flags redact presentation, not storage. State access is credential access.
- API/migration currently share the same schema-owner DB user. Separate DDL/DML
  users are a production hardening opportunity; application owner checks remain
  unchanged and were tested in the preceding local validation.

## Dependency and lifecycle review

APIs precede their dependent resources. DB/user creation precedes the secret
version; workload accounts precede their IAM grants. WIF pool precedes provider
and principal binding. Later Run workloads explicitly depend on secret and SQL
IAM grants. No data migration or job execution is hidden in a provisioner.

The instance is ZONAL, Enterprise edition, PostgreSQL 16, activation policy
ALWAYS, with Terraform and service-level deletion protection enabled. Two
backups are retained; PITR and automatic storage growth are disabled. Monitor
fixed 10 GiB storage to avoid filling the disk. No existing resource replacement
or deletion appears in this plan.

An empty-state create plan cannot prove mutation permissions, organization-policy
compatibility, quota availability, IAM propagation timing or the absence of an
unmanaged same-name resource. A successful apply and live connection checks are
still required later. Do not interpret the plan as deployment verification.

## Expected cost if applied

The only always-on compute in this foundation plan is one Cloud SQL instance.
Official us-central1 prices checked on 2026-11-12:

| SQL cost component  | Assumption                                 | Approximate monthly cost |
| ------------------- | ------------------------------------------ | -----------------------: |
| db-f1-micro compute | $0.0105/hour × 730 hours                   |                    $7.67 |
| SSD                 | $0.000232877/GiB-hour × 10 GiB × 730 hours |                    $1.70 |
| Baseline            | Before backups/network/tax                 |                **$9.37** |
| Used backups        | $0.000109589/GiB-hour × 730 hours          |      About $0.08 per GiB |

Source: [Google Cloud SQL pricing](https://cloud.google.com/sql/pricing).
This excludes existing AWS charges and any paid registry/secret/network usage.
Empty registry and one secret version may fit their free allowances, but account
usage must be considered. No Cloud Run compute is included at this stage.
Stopping SQL stops compute billing, not storage billing. The $5 budget sends
alerts; it is not a spending cap. The SQL baseline alone exceeds it.

## WIF bootstrap and remaining deployment gates

1. Keep Local execution for the first foundation deployment. Human ADC currently
   works; WIF cannot authenticate HCP until the pool/provider/account/binding exist.
2. The current foundation apply would create both WIF and the billable SQL
   instance. It requires a future explicit deployment authorization and a freshly
   reviewed plan. No apply is authorized by this report.
3. After successful bootstrap, set these HCP environment variables:

   ```text
   TFC_GCP_PROVIDER_AUTH=true
   TFC_GCP_RUN_SERVICE_ACCOUNT_EMAIL=peach-terraform@peach-lab9-2026.iam.gserviceaccount.com
   TFC_GCP_WORKLOAD_PROVIDER_NAME=projects/541424029379/locations/global/workloadIdentityPools/peach-hcp/providers/hcp-terraform
   ```

4. Put the required public inputs, including workspace ID, into GCP workspace
   Terraform variables; only then switch GCP execution to Remote and verify a
   remote plan. Never copy human ADC or a service-account key into HCP.
5. Later stages remain image publication, migration-job creation and successful
   execution, API rollout, Firebase enablement/publication and live verification.
   Existing Cognito callback/logout additions need separate approval; this plan
   does not modify AWS. See `LAB9.md` for staged deployment instructions.

No apply/destroy, AWS/Cognito/billing modification, commit or push occurred.
Unrelated local changes, including frontend layout/calendar edits, were preserved.
