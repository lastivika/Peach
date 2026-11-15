# Lab 9 environment readiness — 2026-11-12

> Latest update (2026-11-12): the GCP workspace now exists as
> `ws-V2VUazTYGTjPNfgS`, with Local execution and auto-apply disabled.
> Init/validation and an actual GCP plan succeeded: **37 create, 0 change,
> 0 destroy**. Earlier missing-workspace/no-plan statements below are historical.
> See [the complete plan review](LAB9-PLAN-REVIEW.md) for current evidence.

This is the current readiness record, superseding the environment blockers in the
initial preparation section of `LAB9-VALIDATION.md`. No Terraform apply/destroy,
cloud resource creation, AWS modification, image push, commit or push occurred.

## Installed tools and authentication

| Component                       | Verified state                                                                                                                              |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| Google Cloud CLI                | 593.0.0; official ARM64 archive, SHA256 verified; `~/.local/share/peach-tools/google-cloud-sdk`                                             |
| Firebase CLI                    | 15.36.0; official npm `firebase-tools` package installed with user prefix `~/.local`                                                        |
| Terraform                       | 1.13.5; previously checksum-verified binary moved into `~/.local/bin/terraform`                                                             |
| Docker                          | Client/server 29.7.2; Docker Desktop started and local amd64 build/run verified                                                             |
| gcloud project                  | `peach-lab9-2026`                                                                                                                           |
| GCP project lookup              | ACTIVE, project number `541424029379`                                                                                                       |
| gcloud user login               | Working; authenticated project read succeeded                                                                                               |
| Application Default Credentials | User completed the separate login; `authorized_user`, quota project `peach-lab9-2026`, token refresh succeeded without displaying the token |
| Firebase user login             | Working; project listing succeeded; `peach-lab9-2026` was not listed as a Firebase project                                                  |
| HCP login                       | Existing credentials successfully read workspace metadata; no state or secret variables downloaded                                          |
| AWS login                       | Expired; read-only Cognito domain lookup failed; no live AWS configuration verified or changed                                              |

Commands are available in `~/.local/bin`. If needed in a fresh shell:

```sh
export PATH="$HOME/.local/bin:$PATH"
gcloud version
firebase --version
terraform version
docker info --format '{{.ServerVersion}}'
gcloud config get-value project
```

No service account key was generated or downloaded. The SDK installer used the
existing Python and did not rewrite shell startup files. Firebase npm emitted
upstream dependency-deprecation warnings; installation and CLI execution succeeded.
The disk initially had under 300 MiB free; the owner freed space, allowing the
installations and Docker build. No unrelated source, data, images or volumes were
pruned. Local test containers/networks were removed after tests; the built image
`peach-lab9-cloudrun:local` remains available for inspection.

## Verified cloud metadata; no deployment claims

Read-only service/API checks observed:

- Cloud SQL instance list: empty.
- Workload identity pool list: empty.
- `peach-terraform@peach-lab9-2026.iam.gserviceaccount.com`: HTTP 404.
- Cloud Run services: `SERVICE_DISABLED`; no service inventory claim is possible.
- Artifact Registry repositories: `SERVICE_DISABLED`; no repository inventory
  claim is possible.
- Service Usage listing succeeded. Run, SQL Admin, Artifact Registry, Secret
  Manager, IAM, IAM Credentials, STS, Firebase and Firebase Hosting were not in
  the enabled-service list. The configured Terraform root will enable its
  required APIs only during a future approved apply.

Project billing and the $5 alert budget are owner-provided context; this work did
not alter or independently re-audit billing. Firebase enablement has not been
performed. A successful GCP project lookup does not prove permission to create
all required resources or override organization policies.

## HCP workspace and state isolation

The HCP API verified the existing AWS workspace:

```text
organization: peach-lab7
workspace: peach-dev
id: ws-Z7CeegiCjc7giCYq
working directory: infra
execution mode: remote
auto-apply: true
Terraform version: 1.17.1
```

The lookup of `peach-gcp-dev` returned HTTP 404. Listing the organization's visible
workspaces returned exactly one entry, `peach-dev`. Therefore the GCP workspace
is absent or inaccessible to this principal; it is **not ready**. Do not run
backend initialization that could implicitly create a workspace with defaults.
Do not borrow the AWS workspace, import its state, or alter its auto-apply setting.

`gcp/versions.tf` explicitly selects `peach-lab7/peach-gcp-dev`; it contains only
Google and Random providers and no AWS remote-state reference. The existing
`infra/versions.tf` still selects `peach-dev`.

### Required workspace setup

An organization administrator should create a CLI-driven workspace named exactly
`peach-gcp-dev`, using these prepared settings:

- Execution mode **Local** for human ADC bootstrap; auto-apply **off**.
- Terraform version **1.13.5**, matching the verified local CLI.
- Working directory **gcp**; no VCS auto-run connection during bootstrap.
- Global state sharing **off**. Limit state reads, workspace administration and
  apply permission to authorized people. State will contain the DB password.

`docs/lab9/hcp-workspace.json` is the corresponding API request body for
`POST /api/v2/organizations/peach-lab7/workspaces`. It is a prepared artifact, not
an executed request. Prefer the HCP UI if you do not already have a secure API
workflow; never paste a token into the repository or chat.

After creation, record the immutable `ws-...` ID in ignored `gcp/terraform.tfvars`.
That file has been prepared with the existing **public** Cognito IDs from local
application configuration and both workload flags false. Those IDs were not
verified against live AWS because its session expired. No password is needed.
Then run:

```sh
terraform -chdir=gcp init
terraform -chdir=gcp validate
terraform -chdir=gcp plan
```

**No real plan was run in this session**, because the remote workspace is not
ready. There is no resource-count plan summary. The three successful mocked
Terraform tests are local safety tests, not a real cloud plan. Do not infer a
successful apply, resource existence or quota from them.

## WIF bootstrap dependencies

The configured pool/provider and Terraform service account do not yet exist.
`gcp/federation.tf` is prepared to trust only HCP organization `peach-lab7`,
workspace `peach-gcp-dev`, and its immutable workspace ID. Runtime and migration
service accounts remain separate from the Terraform administrator.

Bootstrap order:

1. Create the HCP workspace above, with Local execution and remote state storage.
2. Fill its immutable ID, use the verified human ADC, and review a GCP-only plan.
3. In a later explicitly authorized deployment session, an apply creates APIs,
   IAM/WIF and the foundation resources. **The current root also creates Cloud
   SQL at this step**, so it is billable and was not executed now. If WIF must be
   provisioned independently earlier, design a separate reviewed bootstrap root;
   do not use an ad-hoc targeted apply or a service account JSON key as a shortcut.
4. Only after the identity exists, set HCP environment variables:

   ```text
   TFC_GCP_PROVIDER_AUTH=true
   TFC_GCP_RUN_SERVICE_ACCOUNT_EMAIL=peach-terraform@peach-lab9-2026.iam.gserviceaccount.com
   TFC_GCP_WORKLOAD_PROVIDER_NAME=projects/541424029379/locations/global/workloadIdentityPools/peach-hcp/providers/hcp-terraform
   ```

5. Transfer public Terraform inputs into the dedicated HCP workspace variables,
   switch execution mode to Remote, and verify a reviewed remote plan. Do not
   copy human ADC into HCP. If connecting VCS later, restrict trusted branches and
   use `gcp/**` run triggers; leave AWS `infra` and its workspace untouched.

These are expected identity names from code, not evidence of existing resources.
The present trust is for HCP only; GitHub app deployment needs a separately scoped
repository/environment WIF configuration if added later.

## Cognito additive changes prepared, not applied

`docs/lab9/cognito-firebase.patch` is a reviewable patch against `infra/auth.tf`.
`git apply --check` passed. It was **not applied** to the active AWS configuration.
It retains the existing CloudFront and localhost callback/logout entries and adds
both Firebase hostnames with the exact `/auth/callback/` redirect used by Peach's
OIDC manager, its legacy `/callback` alias and the `/` logout path.

The AWS workspace currently has auto-apply enabled, so do not commit/merge this
patch into active `infra/` casually. After separately approving the AWS change,
refresh AWS authentication, read the live user-pool client, compare its settings
with Terraform, apply the patch to a review branch, and inspect the full plan.
Accept only the intended callback/logout additions. Preserve authorization-code
flow, scopes, providers, token lifetimes, rotation/revocation and every existing
URL. Do not use a partial `update-user-pool-client` command; omitted fields can
reset. Never replace `site_url` with the Firebase URL.

Optional parser CORS must likewise gain the two Firebase origins without losing
the AWS origin before setting `NEXT_PUBLIC_AGENDA_PARSER_URL`. Manual agenda editing
remains functional when the parser is unavailable. The GCP root does not own or
mutate any of these AWS resources.

## Local verification in this continuation

- Built `backend` target `cloudrun`, linux/amd64, local image ID
  `sha256:78f8f0eddafcb512a880a9a2b0bdfdfcf9da26581da94a0bd92d45503e071c0e`.
  This is a local image ID, **not** an Artifact Registry deployment digest.
- Image ran as `app`, honored `PORT=9097`, and returned healthy without a DB or
  startup migrations. Missing and malformed tokens returned 401 on protected APIs.
- The same built image applied migrations to an empty PostgreSQL 16 container,
  reached `0005 (head)`, and passed DB readiness plus allowed/denied CORS checks.
- Full backend suite: **64 passed** against a disposable local PostgreSQL 16 DB.
- Repository unittest suite: **17 passed**. Backend/new-test Ruff lint and format:
  passed (53 files).
- Frontend: **24 tests passed**, ESLint, Prettier and TypeScript passed; the actual
  `scripts/gcp/build-frontend.sh` helper completed with dummy public settings and
  all seven app routes exported. This bundle must not be published as a real site.
- Terraform format, provider schema validation and all **3 mocked plans** passed.
- Firebase Hosting emulator: all seven app routes passed, including trailing-slash
  callback query preservation; an unknown route returned 404. The emulator is
  configured on `127.0.0.1:55009` to avoid the macOS service occupying port 5000.
  Real Cognito login and live Hosting are still unverified.
- The first Hosting check failed because Firebase moved from occupied port 5000
  to 5002 while the check requested 5000. The configured loopback port fixed it;
  the retry passed. A nonfatal demo-project metadata lookup returned 403, as
  expected for a demo project that does not exist in GCP. No API was enabled.
- HCP's first Python HTTPS request failed certificate verification with the system
  defaults; using the installed trusted CA bundle fixed it without disabling TLS.
- ADC was initially missing after regular CLI login; the owner completed the
  separate ADC flow and the final refresh succeeded. Docker's socket disappeared
  during environment cleanup; restarting Docker resolved the build failure.
- See `LAB9-VALIDATION.md` for prior preparation history.

## Remaining deployment gates

1. Create/access the dedicated HCP workspace and fill its ID; review a real plan.
2. Verify live Cognito configuration with a refreshed AWS session; separately
   authorize its additive callback/logout changes (and parser CORS if desired).
3. Agree on the billable demo window and cleanup. After future approval: foundation
   apply, Firebase enablement, image push, migration job creation/execution, API
   rollout, real-config frontend build/Hosting deployment, and live verification.
4. Complete the actual Moodle cost calculations and separately authorized demo
   evidence listed in `LAB9-SUBMISSION.md`. Do not substitute local tests for the
   required live application URL or three demo screenshots.
