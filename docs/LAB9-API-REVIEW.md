# Cloud Run API approval review — 2026-11-14

> Approved API apply completed: 2 added, 0 changed, 0 destroyed. Live HTTPS and database readiness passed; final plan has no changes. See [deployment evidence](LAB9-DEPLOYMENT.md). Pending statements below are the historical pre-apply review.

## Fresh real Terraform plan

Baseline: no changes. API-only plan: **2 create, 0 change, 0 destroy**:

- google_cloud_run_v2_service.api[0] — peach-api
- google_cloud_run_v2_service_iam_member.browser[0] — roles/run.invoker for allUsers

All 38 existing resources, including the migration job, database and secret,
remain unchanged. No replacements, AWS resources, new SQL instance or Firebase
resources are targeted. No apply has run. The saved plan is in a private temporary
directory; its path/hash and sanitized service configuration are recorded in
ignored submission/lab9/api-plan-review.json. enable_api=true was supplied as a
plan-only CLI override; persist it in ignored tfvars after approval to avoid a
later plan proposing removal of an approved service.

## Runtime and identity

- Project peach-lab9-2026; region us-central1; Gen2 execution.
- Image: `us-central1-docker.pkg.dev/peach-lab9-2026/peach/backend@sha256:732296032c544396b74c4f19daf1c43e6ce50918b4d20c5e21f92446ead091db`.
- Image digest matches the successful live migration execution; the local image
  ID matches the recorded linux/amd64 build that passed health and auth smoke tests.
- Dedicated runtime identity peach-api@peach-lab9-2026.iam.gserviceaccount.com.
  Live IAM confirms Cloud SQL client and secret-specific Secret Accessor; no
  infrastructure-admin project roles are assigned to this runtime identity.
- Existing Cloud SQL socket: /cloudsql/peach-lab9-2026:us-central1:peach-postgres.
- DATABASE_URL from existing peach-database-url version 1, currently ENABLED.
  Its previously verified target is database peach. No password is in public env.
- Min instances 0; max instances 1; 1 CPU; 512 MiB; concurrency 8; timeout 60s.
- Request-based CPU allocation (cpu_idle=true); port 8080; nonroot container.
- Startup/liveness checks use /health; readiness /api/v1/health/ready runs SELECT 1.
- APP_ENV=production, DB_POOLING=false; existing public Cognito region/pool/client
  IDs; CORS permits the two intended Firebase origins. No AWS credentials supplied.
- No startup migrations: the dedicated job already applied Alembic revision 0005.

## Authentication review

items, meetings and me require CurrentUser. Verification uses Cognito JWKS with
RS256, configured issuer/audience, required expiry/sub/token_use and ID-token
semantics. Missing credentials yield 401; absent auth configuration fails closed
with 503. Invalid tokens are rejected. Item/meeting access filters by owner_id.
The public Run invoker binding allows browsers carrying Cognito tokens to reach
FastAPI; it does not remove application authentication. CORS is not authentication.
Health/readiness, docs, Redoc and OpenAPI are intentionally unauthenticated and do
not provide application data. Readiness only executes SELECT 1 and reports status.

Historical local smoke evidence: health 200 and unauthenticated protected routes
401. Live service HTTPS, readiness, invalid-token handling and logs cannot be
verified until the user approves creation. No authenticated data-read success is
claimed. That check requires a valid existing Cognito session. Firebase sign-in
also requires separately approved callback/logout additions; neither requirement
will be bypassed by disabling token validation.

## Additional cost estimate

No additional fixed database cost. Existing SQL baseline remains approximately
$9.37/month plus backups/usage. Min-zero Run does not reserve an idle instance,
but active requests/startup/shutdown and related network/logging usage can bill.
At us-central1 request-based list rates, 1 vCPU + 0.5 GiB costs approximately
$0.00002525 per active instance-second, plus $0.40 per million requests, before
shared free allowances. For illustration, 10,000 requests consuming 10,000 total
active instance-seconds cost about $0.26 before free allowances, network, logs
and startup overhead. This is an explicit example, not a monthly forecast or cap.
Small lab use may fit unused free allowances; no guaranteed zero cost is claimed.
Maximum instance settings are scaling controls, not a billing cap.

Source checked: https://cloud.google.com/run/pricing.

## After approval

Apply only this two-resource plan (refresh/review again if state or configuration
changes), record the real HTTPS URL and deployed digest, verify ready conditions,
liveness/readiness, 401 responses for missing/invalid tokens and allowed/denied
CORS origins; inspect service logs for unexpected errors. Run a final consistency
plan and expect 40 managed resources. Verify an authenticated database read with
a legitimate Cognito session when available; report any login blocker.

Firebase Hosting publication and Cognito changes remain separately gated. No AWS,
Cognito, billing, frontend publication, commit, push or destroy was performed.
