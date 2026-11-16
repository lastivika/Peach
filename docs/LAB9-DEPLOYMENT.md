# GCP foundation deployment — 2026-11-14

> Frontend is published at https://peach-lab9-2026.web.app and Cognito callback/logout URLs were extended additively. Remaining: authenticated browser test, cost table, three Part 4 screenshots, commit/PR.

## Firebase Hosting published and Cognito extended — 2026-11-14

Cognito client `peach-web` (pool us-east-1_gfkwmAkKP) changed only
CallbackURLs and LogoutURLs. All existing localhost and CloudFront URLs remain;
added `/auth/callback/` callbacks and `/` logout URLs for both
peach-lab9-2026.web.app and peach-lab9-2026.firebaseapp.com. Flows, scopes,
identity providers, token validity, revocation and refresh rotation are unchanged.
The `/callback` variants were not added (the SPA uses `/auth/callback/`).

Firebase Hosting release of version 508f4500abaf4c35 on the live channel
completed at 2026-11-14T21:02Z (CLI exit 0, manifest verified).

Read-only checks on 2026-11-15:

- `/`, `/items`, `/calendar`, `/home`, `/login/` and `/auth/callback/?code=x&state=y`
  return 200; an unknown path returns the exported 404 page.
- Built JS targets https://peach-api-u2sij2lmoa-uc.a.run.app and the public
  Cognito client ID. No DB URL or secret values are present; `client_secret`
  matches are oidc-client-ts parameter names only.
- API readiness 200 (DB SELECT 1); CORS preflight from the Firebase origin 200.

Still pending: sign-in through the Firebase URL with two synthetic users, one
authenticated task/meeting read from Cloud SQL (the Moodle "API reads the
database" evidence), and cross-user isolation checks.


## Cloud Run API deployed and verified — 2026-11-14

API URL: [https://peach-api-u2sij2lmoa-uc.a.run.app](https://peach-api-u2sij2lmoa-uc.a.run.app)

Ready revision: `peach-api-00001-f7m`.

The user explicitly approved the API service and reviewed allUsers invoker binding.
Before apply, the tested image's application source hashes matched reviewed local
code, and its OpenAPI data routes declared authentication. Manual source review
confirmed router-level Cognito validation, per-route CurrentUser dependencies,
and owner-scoped queries for all data operations. No administrative endpoints
were found. Health/readiness and docs/OpenAPI remain public, as reviewed.

The refreshed plan exactly matched the saved review: **2 creates, 0 changes,
0 destroys**. Apply succeeded with **2 added, 0 changed, 0 destroyed**. Existing
Cloud SQL, secret version 1, migration job and image were reused unchanged.
Ignored tfvars now retains enable_api=true so subsequent plans preserve the API.

Live checks passed:

- Service ready condition succeeded; pinned image digest matches the tested build.
- HTTPS /health returned 200 with status ok.
- HTTPS /api/v1/health/ready returned 200 with database ok (real SELECT 1).
- All 12 protected route/method combinations rejected missing credentials with
  401, including read/create/update/delete items/meetings and agenda update.
- Malformed bearer tokens returned 401 on items, meetings and me.
- Firebase-origin CORS preflight returned 200 with its exact allowed origin;
  unrelated-origin preflight returned 400 without an allow-origin header.
- Log query since service creation found zero ERROR-or-higher entries and zero
  HTTP 5xx entries at verification time. Logging can be delayed; this is a bounded
  observation, not a guarantee about future requests.
- Terraform state now has **40 managed resources**. Final real plan: **no changes**.
- Live scaling remains min 0/max 1; 1 vCPU, 512 MiB, request-based allocation.

Authenticated application-data reads and cross-user isolation have not been
verified live: they require legitimate Cognito user sessions. No authentication
was weakened, no tokens were requested in chat, and no successful data mutation
was performed by the unauthenticated verification requests.

No AWS/Cognito/billing changes, additional databases, Firebase Hosting deployment,
commit, push or destroy occurred. Expected incremental API costs remain the
reviewed usage-based estimate; no unexpected infrastructure tier was introduced.

Evidence: ignored submission/lab9/api-apply-result.json,
api-live-verification.json and api-consistency.json. Next steps are the separately
approved Cognito callback/logout additions, Firebase enablement/build/publication,
and private-browser authenticated user workflows. Build frontend against the
verified HTTPS URL above and scan final static assets before publication.


> API preparation: [LAB9-API-REVIEW.md](LAB9-API-REVIEW.md). Fresh plan is 2 creates, 0 changes, 0 destroys; API apply awaits explicit approval.

## WIF and migration completed — 2026-11-14

The explicitly approved HCP speculative test succeeded:
[run-es6xytQzBSzbJ5eB](https://app.terraform.io/app/peach-lab7/workspaces/peach-gcp-dev/runs/run-es6xytQzBSzbJ5eB).
It used HCP dynamic GCP credentials and refreshed the foundation with **0 creates,
0 changes, 0 destroys**. No apply was possible for the speculative configuration.
Only peach-gcp-dev temporarily used Remote; Local was restored afterward and
auto-apply remained disabled. The same immutable HCP state version
sv-S1DWMuTtWjHDQvUm, serial 3, was present before and after the WIF test.
Local terraform state-pull byte checksums varied, so they were not used as proof;
the authoritative HCP state-version identity and serial establish no state write.
The three non-secret TFC_GCP environment variables remain configured for future
remote use. Public foundation inputs were provided in the narrowly scoped test
configuration archive, not as persistent workspace Terraform variables. Before
future remote runs, supply the current image/workload inputs; the old foundation
archive does not represent the now-deployed migration job. No ADC or JSON key
was uploaded. AWS workspace peach-dev was not modified.

Before migration, read-only SQL checks confirmed an empty public schema in
peach on peach-lab9-2026:us-central1:peach-postgres. The existing secret version 1
was checked in memory for this exact database/socket target, without exposing
its value. Image migration source hashes matched reviewed local sources.
Revision 0002 intentionally maps is_done to status and drops the intermediate
is_done column; on this empty database it removes no pre-existing application
data. No downgrade or unexpected destructive upgrade was executed.

The refreshed job plan exactly matched the reviewed configuration:
**1 create, 0 changes, 0 destroys**. Apply succeeded with the same counts.
Ignored gcp/terraform.tfvars now records the pinned image,
enable_migration_job=true and enable_api=false to preserve the deployed job.

Live job configuration was checked before submitting exactly one execution:
peach-migrate-q5xfx. It used the dedicated peach-migrate identity, existing SQL
socket and secret version, command alembic upgrade head, one task, zero retries,
600-second timeout, and the reviewed immutable image. Execution completed
successfully with **1 succeeded, 0 failed**. No retry execution was submitted.

Independent read-only verification confirmed Alembic **0005** and tables:

- alembic_version
- items (status and owner_id; no obsolete is_done)
- users (Cognito subject, email and name)
- meetings (owner_id, agenda and ai_suggestion)

Final Terraform state has **38 managed resources** (37 foundation plus migration
job); the final real plan returned exit 0, **no changes**. Cloud Run services
remain empty. No API or Firebase Hosting deployment, Cognito change, billing
change, AWS modification, commit, push or destroy occurred.

Evidence is retained in ignored submission/lab9/wif-test-result.json,
migration-job-apply.json, migration-execution.json, migration-schema-before.json,
migration-schema-after.json and migration-consistency.json. No secret payloads
are present in these reports.

Next: prepare/review the API-only plan (service plus invoker binding) and obtain
approval; verify API readiness, database connectivity, auth failures and CORS.
Then approve Firebase enablement/publication and, separately, additive Cognito
callback/logout changes. Build frontend against the verified API URL, scan its
export and test sign-in and user isolation in a private browser. Existing AWS
parser CORS and report/data-source differences remain separate integration work.


## Completed recovery — 2026-11-14

The user explicitly approved the three-resource recovery. Before execution,
the reviewed recovery file hash was checked and a refreshed real plan was
compared with it: exactly three creates, identical resource values, no changes,
no destroys, and no action on the Cloud SQL instance.

**Recovery apply succeeded: 3 added, 0 changed, 0 destroyed (exit 0).**
A subsequent authenticated plan returned exit 0: **no changes**. Terraform state
contains exactly all 37 resource addresses from the original approved foundation.

Live verification confirms:

- SQL remains RUNNABLE, db-f1-micro, PostgreSQL 16, ZONAL, 10 GiB SSD.
- Database peach and database user peach now exist.
- Secret peach-database-url has exactly one ENABLED version; secret payload was
  not printed or retrieved during live verification.
- SQL authorized networks remain empty and ssl_mode is ENCRYPTED_ONLY.
- Artifact Registry, IAM grants and all three enabled service accounts exist.
- WIF pool/provider are ACTIVE with the reviewed workspace-restricted binding.
- No user-managed service-account keys, Cloud Run services or Cloud Run jobs.

No instance replacement, new paid instance, AWS/Cognito/billing modification,
Hosting deployment, commit or push occurred. Expected SQL baseline remains
$9.37/month plus backups and usage, consuming eligible trial credit. A live billed
cost total was not queried; this remains an estimate.

HCP is still Local with auto-apply disabled. End-to-end HCP WIF authentication
remains to be tested before switching to Remote. Application schema migrations,
image publication, API deployment and Firebase Hosting remain separate later
stages. This verification establishes infrastructure configuration, not a tested
application/database connection or completed application schema.

Evidence: ignored submission/lab9/foundation-complete.json,
recovery-apply-result.json and live-verification.json. Private plan/apply logs
remain outside Git. Earlier partial-apply history below is retained for audit
and its pending steps are superseded by this completion record.

## Billing and authorization

Read-only console inspection confirmed Free Trial status, $300.00 available,
89 days remaining, and credit expiration February 11, 2027. Billing account
(ID redacted) is linked to peach-lab9-2026. No upgrade or billing-setting
change was made. The user authorized only the reviewed 37-resource foundation.
The saved plan SHA-256 matched before execution.

## Apply result and recovery

Terraform apply exited 1: DNS lookup of sqladmin.googleapis.com failed while
polling the Cloud SQL creation operation. Terraform reported 33 creations
completed. Google nevertheless completed peach-postgres; a subsequent live API
check confirmed RUNNABLE. The instance had not been saved in Terraform state.
It was successfully imported into the isolated GCP workspace; no second SQL
instance was created.

Current state therefore contains 34 of the 37 approved resources. The recovery
plan is exactly 3 create, 0 change, 0 destroy, with no replacement:

- google_sql_database.peach
- google_sql_user.peach
- google_secret_manager_secret_version.database

This recovery plan has NOT been applied. The original saved plan is stale after
partial apply and import and must not be reused. The protected recovery plan path
and hash are recorded in ignored submission/lab9/recovery-plan-summary.json.
Because authorization was conditional on the unchanged saved plan, recovery apply
is paused for approval of this new three-resource plan.

## Verified real resources

- All 11 API resources completed, as recorded by Terraform.
- Artifact Registry peach in us-central1 exists, format DOCKER.
- Service accounts peach-api, peach-migrate, peach-terraform exist and are enabled;
  none has user-managed keys.
- Two workload Cloud SQL client grants and nine Terraform administration grants
  appear in live project IAM. Secret-specific accessor grants are present for
  the two workload accounts.
- WIF pool peach-hcp and provider hcp-terraform are ACTIVE. Issuer, organization,
  workspace name and immutable workspace ID condition match the reviewed setup.
  Workload Identity User binding is restricted to ws-V2VUazTYGTjPNfgS.
- SQL peach-postgres is RUNNABLE: PostgreSQL 16, db-f1-micro, ZONAL, 10 GiB SSD,
  empty authorized networks, ENCRYPTED_ONLY. Only default postgres database/user
  exist; the Peach database/user are pending.
- Secret peach-database-url exists; it has zero versions until recovery completes.
- Cloud Run services and jobs are empty in us-central1. No Hosting deployment ran.
- The generated password is held in Terraform state, never printed in logs.

Google-managed service identities appear in project IAM. A default Compute
service-account Editor grant also exists outside this Terraform root. Its origin
was not established; no change was made to it. Review least privilege separately.

WIF infrastructure is verified, but an HCP-issued OIDC exchange and remote plan
have not been tested. HCP remains Local with auto-apply disabled. Dynamic HCP
credential variables and the transition to remote execution remain pending;
never upload ADC or service-account keys. AWS and Cognito were not modified.

## Costs and remaining work

The running SQL instance now consumes trial credits. Estimated compute plus
10 GiB SSD is $9.37/month, plus backup/network/other usage. This is not a spending
cap or a live billing total; billing reports can lag. No additional compute tier
or billable instance was introduced by recovery.

Next: approve/apply the three-resource recovery plan, verify the database/user and
secret-version metadata, run a no-change consistency plan, and then validate HCP
WIF authentication before changing execution mode. Image publication, migrations,
API rollout and frontend publication are later separate stages.

To pause SQL compute later, set activation policy NEVER using a reviewed change;
storage/backups continue consuming credits. A later deletion requires explicit
authorization, disabling both deletion protections, reviewing a GCP-only destroy
plan and handling retained backups. Neither stop nor destroy was run here.
Export any required data before the trial expires; do not upgrade billing.
