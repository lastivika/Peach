# Lab 9 preparation validation — 2026-11-12

> Current application preparation: [LAB9-APPLICATION-REVIEW.md](LAB9-APPLICATION-REVIEW.md). Foundation is deployed; historical preparation-only statements below are superseded by the deployment record.

> Latest update (2026-11-12): the GCP workspace now exists as
> `ws-V2VUazTYGTjPNfgS`, with Local execution and auto-apply disabled.
> Init/validation and an actual GCP plan succeeded: **37 create, 0 change,
> 0 destroy**. Earlier missing-workspace/no-plan statements below are historical.
> See [the complete plan review](LAB9-PLAN-REVIEW.md) for current evidence.

## Current continuation status

The environment was advanced later on the same date. See
[LAB9-ENVIRONMENT.md](LAB9-ENVIRONMENT.md) for verified CLI installations, working
user login/ADC, HCP workspace absence, API/federation metadata, successful Docker
build/runtime/migration checks, and remaining deployment gates. The official
Moodle requirements are now reconciled in [LAB9-SUBMISSION.md](LAB9-SUBMISSION.md).
The initial missing-CLI, stopped-Docker and missing-Moodle blockers below are
historical and have been resolved. The GCP workspace is still not ready, so no
real Terraform plan was run.

Continuation verification also passed the Firebase Hosting emulator: seven app
routes, trailing-slash callback with query parameters, and an unknown-path 404.
Port 5000 conflicted with a macOS listener; `firebase.json` now fixes the emulator
to loopback port 55009. No Firebase deployment was performed.

## Initial preparation record (historical)

All results below are local checks. No live cloud deployment, authenticated GCP
plan, apply, destroy, registry push, Firebase publication or AWS change occurred.

## Passed

| Check                                          | Observed result                                                                                         |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Terraform 1.13.5 `fmt -recursive -check`       | Passed                                                                                                  |
| `init -backend=false`                          | Passed; no HCP state connection; signed Google 7.46.2 / Random 3.9.1 installed and locked               |
| Terraform `validate`                           | Passed against installed provider schemas                                                               |
| Terraform `test`                               | 3 mocked plans passed: no workload on bootstrap, API gate, next-release migration without API promotion |
| Backend Ruff lint and format                   | Passed, 52 existing Python files                                                                        |
| Backend pytest                                 | **64 passed**, fresh UTF-8 PostgreSQL 16 test database                                                  |
| Alembic on a separate empty database           | All five revisions applied, `current` returned `0005 (head)`                                            |
| SQLAlchemy/asyncpg Unix-socket URL             | Alembic used the same `?host=/socket/path` URL structure as Cloud Run (local socket plus test port)     |
| Repository unittest suite                      | **17 passed**, including existing AWS safety tests and new Cloud Run startup contract                   |
| Frontend Vitest                                | **24 passed**, including the user's existing calendar tests                                             |
| Frontend ESLint, Prettier and `tsc --noEmit`   | Passed                                                                                                  |
| Next.js static export (`next build --webpack`) | Passed with public dummy build configuration; all seven real routes plus 404 present                    |
| Firebase JSON parsing, shell syntax            | Passed                                                                                                  |
| Diff whitespace and new file formatting        | Passed                                                                                                  |

Terraform mocks test configuration behavior; they do not verify IAM enforcement,
service quotas, API availability or real resource creation. The Unix-socket test
verifies driver compatibility, not the managed Cloud SQL proxy. The static export
proves build compatibility, not OAuth redirect registration or live browser CRUD.
The validation bundle uses example IDs and must not be published as a deployment.

Reproduction commands (after dependencies are installed):

```sh
terraform -chdir=gcp init -backend=false
terraform -chdir=gcp fmt -recursive -check
terraform -chdir=gcp validate
terraform -chdir=gcp test
backend/.venv/bin/python -m unittest discover -s tests -v
(cd backend && .venv/bin/ruff check . && .venv/bin/ruff format --check .)
(cd frontend && pnpm test && pnpm lint && pnpm format:check && pnpm exec tsc --noEmit)
```

For backend integration tests, supply `TEST_DATABASE_URL` pointing only to a
fresh disposable **UTF-8** local database before running `pytest -q` in `backend`.
The fixture drops/recreates its tables. Never point it at application or cloud
data. This run used an isolated temporary PostgreSQL 16 cluster on localhost port
55439; it was stopped after verification. Migrations used a second empty database.
For a real frontend build use the public configuration and helper in the runbook.

## Failed attempts and their resolution

- Terraform initially rejected a single-line nested HCL block. Corrected it;
  final format, validate and mocked plans passed.
- Provider installation, initial PostgreSQL init and Next cache writes initially
  hit `ENOSPC`. Removed only regenerable `.next/cache`, partial newly downloaded
  provider files and the temporary CLI download archive; retries passed. Disk
  remains tight; allow additional space before building Docker images.
- A sandboxed Next build could not resolve Google Fonts. Retried with network
  permission; the existing fonts and static build succeeded without UI changes.
- A sandboxed Terraform validation could not start provider IPC. Local validation
  outside that sandbox succeeded; no cloud authentication was involved.
- The first selected backend test run had 31 passes and one setup error because
  Compose hostname `db` was unavailable. A temporary local PostgreSQL server was
  used instead of existing databases.
- The first full local DB run had 63 passes and one Ukrainian JSONB test failure
  because `initdb --no-locale` selected SQL_ASCII. Created fresh UTF-8 databases;
  all 64 tests passed. GCP database encoding is explicitly UTF8.
- New startup test import sorting initially failed Ruff; fixed and rechecked.
- Docker socket access initially failed in the sandbox; an authorized local check
  confirmed the Docker daemon is not running. **Image build/run remains blocked.**

## Remaining blockers / required evidence

1. `gcloud` and `firebase` are absent from PATH. Install their official CLIs and
   perform the ADC/Firebase login steps in `LAB9.md`. No GCP identity, project
   permissions, quota, org policy or billing status was verified remotely.
2. Create/configure the separate HCP workspace, public Cognito inputs and WIF
   bootstrap. No real Terraform plan has been run; review one before deployment.
3. Start Docker and free adequate disk space, then locally build the `cloudrun`
   target for linux/amd64. Its image execution, registry upload, Cloud SQL proxy,
   Cloud Run migration execution and API health remain unverified.
4. Firebase Hosting emulator/live routing and real OAuth flow have not been run.
   The existing Cognito callback/logout list blocks Firebase sign-in until an
   authorized additive AWS change. Optional parser CORS similarly needs approval.
5. The original Moodle text specifying the four exact deliverables was not
   attached. The runbook contains four provisional evidence bundles to reconcile
   with that rubric, not an invented statement of the assignment requirements.
6. Continuous Cloud SQL operation exceeds the $5 budget alert. Agree on the
   billable demonstration window and cleanup before the first apply.

## File inventory and preservation

Created:

- `gcp/versions.tf`, `variables.tf`, `main.tf`, `run.tf`, `federation.tf`,
  `outputs.tf`, `terraform.tfvars.example`, `.terraform.lock.hcl`,
  `tests/safety.tftest.hcl`.
- `backend/scripts/cloud-run.sh`, `scripts/gcp/build-frontend.sh`, `firebase.json`.
- `tests/test_gcp_startup.py`, `docs/adr/0009-gcp-multicloud.md`, `docs/LAB9.md`,
  this validation record.

Modified: `README.md`, `.gitignore`, `backend/Dockerfile`, `backend/.dockerignore`.
The GCP Docker stage is before the existing final Lambda stage, so the previous
unnamed default build target and AWS runtime commands remain unchanged. Locked
application dependencies and deployed image digests make releases repeatable;
base image tags and the inherited UV builder tag remain mutable, so rebuilding
later is not claimed to be bit-for-bit identical.

Preserved existing user changes to `frontend/.prettierignore`,
`frontend/components/calendar.tsx` and `frontend/tests/calendar.test.tsx`.
No `infra/`, AWS scripts/workflows, HCP AWS workspace or cloud resources were
modified. No commit, push or merge was performed. Existing CI deploys AWS on main;
review that behavior before any future push/merge of this preparation.
