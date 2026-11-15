# Peach application deployment review — 2026-11-14

> WIF test and migration job deployment/execution completed successfully. See [deployment results](LAB9-DEPLOYMENT.md). Plans and pending statements below describe the earlier approval review. API and Hosting remain undeployed.

## Ready for approval

The foundation was reverified through live Google APIs and a refreshed ADC-backed
Terraform plan: no changes. All 37 foundation resources remain managed.
SQL is RUNNABLE and a read-only connection using the existing database URL secret
through Google's official Cloud SQL Auth Proxy passed SELECT 1. The database has
no alembic_version table yet. No migrations were executed.

Production image was built from the current working tree using the cloudrun
Docker target, linux/amd64, frozen dependencies and a unique image-ID tag, then
pushed to the existing repository under the user's explicit image-push request:

`us-central1-docker.pkg.dev/peach-lab9-2026/peach/backend@sha256:732296032c544396b74c4f19daf1c43e6ce50918b4d20c5e21f92446ead091db`

The local image uses nonroot app, excludes local .env files, reports Alembic head
0005, returns health 200 and rejects unauthenticated items/me/meetings with 401.
Short-lived ADC registry authentication was held in a temporary Docker config,
removed after push. No keys were created. Local verification containers were removed.

Checks passed: 17 repository tests, 3 mocked Terraform safety tests, Terraform
validation/fmt, 24 frontend tests and TypeScript noEmit. The latest image build
and local smoke checks passed; prior full integration tests remain historical.

## Concrete plans (not applied)

Protected binary paths and hashes are in ignored
submission/lab9/application-plans.json. CLI variable overrides were used so local
foundation tfvars remain unchanged until deployment approval.

1. Migration stage: **1 create, 0 change, 0 destroy** —
   google_cloud_run_v2_job.migrate[0]. Dedicated peach-migrate service account,
   existing secret version 1, existing SQL socket, command alembic upgrade head,
   one task, parallelism 1, zero retries, timeout 600 seconds, 1 CPU/512 MiB.
2. Combined API preview: **3 create, 0 change, 0 destroy** — migration job,
   google_cloud_run_v2_service.api[0], and its browser invoker binding. This is
   a preview only: deploy API after successful migration, refreshing its plan.
   API uses peach-api identity, the same immutable digest, min 0/max 1 instance,
   concurrency 8, request-based billing, 1 CPU/512 MiB, existing SQL/secret.

Neither plan modifies or replaces SQL or any foundation object. No AWS provider
or AWS changes are present. Public Run transport does not remove FastAPI Cognito
ID-token validation or owner checks. Approval is required before apply or job
execution. Persist the reviewed image and enable flags in ignored tfvars when
approved so subsequent plans retain deployed workloads.

## HCP WIF prerequisite

Live pool/provider are ACTIVE and the reviewed issuer, organization, workspace
name/ID condition and workloadIdentityUser binding match. This is configuration
verification, not an end-to-end authentication test. The GCP workspace is Local,
auto-apply false, directory gcp, Terraform 1.13.5, with no workspace variables.
Local execution cannot issue an HCP run's workload identity token.

Proposed test, requiring approval of workspace configuration changes:
configure these environment variables plus the existing public Terraform inputs,
keep both workload flags false for the foundation test, temporarily use Remote,
upload only the necessary gcp configuration and lockfile, and run a speculative
plan (no apply). Restore Local after the test, keeping auto-apply disabled.
This test requires temporarily changing execution mode before authentication can
be proven; it cannot satisfy the earlier instruction to prove remote credentials
before any Remote-mode change without an explicit exception.

- TFC_GCP_PROVIDER_AUTH=true
- TFC_GCP_RUN_SERVICE_ACCOUNT_EMAIL=peach-terraform@peach-lab9-2026.iam.gserviceaccount.com
- TFC_GCP_WORKLOAD_PROVIDER_NAME=projects/541424029379/locations/global/workloadIdentityPools/peach-hcp/providers/hcp-terraform

Never upload human ADC, JSON keys, Terraform state or secret values in the
configuration bundle. AWS workspace peach-dev remains outside the test.

## Frontend and authentication

Firebase management API returned 404 for the project: Firebase enablement remains
pending; this check did not enable it. Intended URLs, not deployed URLs:
https://peach-lab9-2026.web.app and https://peach-lab9-2026.firebaseapp.com.
No Cloud Run URL exists yet. Build final static assets only after obtaining and
verifying the actual API endpoint; do not publish the earlier dummy export.
Secret scanning of that final export and private-browser tests are pending.

The review-only docs/lab9/cognito-firebase.patch applies cleanly to current
infra/auth.tf and retains existing callbacks/logout URLs. Required additions:

Callbacks:
- https://peach-lab9-2026.web.app/auth/callback/
- https://peach-lab9-2026.web.app/callback
- https://peach-lab9-2026.firebaseapp.com/auth/callback/
- https://peach-lab9-2026.firebaseapp.com/callback

Logout:
- https://peach-lab9-2026.web.app/
- https://peach-lab9-2026.firebaseapp.com/

The actual SPA uses authorization code flow and ID tokens; FastAPI validates
issuer, audience, expiry and token_use. Live Cognito settings were not modified
or freshly inventoried. Before applying an approved AWS change, refresh the live
client and preserve all existing settings; do not send a partial replacement
update. Cognito modification needs separate explicit approval.

Existing AWS integrations are preserved. Optional parser support from Firebase
needs an additive AWS parser CORS approval; until then set the public parser URL
empty and verify manual agenda functionality. Existing AWS reports do not
implicitly query the new GCP database.

## Incremental cost and evidence

No new database is proposed. Existing SQL baseline remains approximately
$9.37/month plus backups/usage. Cloud Run at min zero has no reserved idle instance;
requests, startup, executions, logs and network can consume credits. A single
1-vCPU/0.5-GiB migration limited to 600 seconds is roughly $0.011 before free
allowances using Tier 1 job compute rates; retries are disabled. Registry storage
above the shared 0.5-GiB allowance is approximately $0.10/GiB-month. Low lab traffic
may fit free allowances, but they are shared and not guaranteed. No billing
upgrade or budget change is proposed.

Sources: https://cloud.google.com/run/pricing and
https://cloud.google.com/artifact-registry/pricing.
HCP behavior: https://developer.hashicorp.com/terraform/cloud-docs/workspaces/run/remote-operations
and https://docs.hashicorp.com/terraform/cloud-docs/dynamic-provider-credentials/gcp-configuration.

Moodle still requires: approved commit/PR link with gcp/ and ADR; working GCP
frontend plus an API database read; AWS/GCP cost comparison for 0, 20, 176 and 730
active hours/month; three screenshots (BigQuery query with bytes processed,
Looker Studio chart, Document AI or Vision OCR result). None of the three extra
service exercises was provisioned by this application preparation.
