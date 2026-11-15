# Peach

A private task board with Next.js, FastAPI, PostgreSQL and Cognito sign-in.

## Development

Copy `.env.example` to `.env`, configure Cognito values, then run `make up`.
Use `make lint` and `make test`. AWS credentials and `.env` must never be committed.

## Calendar and meetings

Signed-in users can open **Calendar** from the navigation to manage their own
meetings. The month view can be navigated with the previous/next buttons; select
a date to see its meetings. Meetings store timezone-aware start and end times,
which the browser displays in local time. Meeting locations can be rooms or
HTTP/HTTPS links. Apply the database migration with `make migrate` after
updating the backend; it adds the owner-scoped `meetings` table.

The API is under `/api/v1/meetings`: list with required `start` and `end`
ISO-8601 timestamps, create with POST, retrieve by ID, update with PATCH, and
delete with DELETE. The server derives the owner from the authenticated token.

## Weekly meetings report lab

The optional report pipeline is described in
[`docs/WEEKLY-MEETINGS-REPORT.md`](docs/WEEKLY-MEETINGS-REPORT.md). It queries
the existing owner-scoped `meetings` table and does not create another data
store. Its separate CloudFormation stack is not deployed by the normal Peach
release workflow, and its weekly schedule defaults to disabled.

## AWS deployment

See [AWS lab guide](docs/AWS-LAB.md) for architecture, setup, CI/CD, tradeoffs, rollback and teardown.
`make deploy-backend` builds a SHA-tagged ECR image, migrates and updates ECS Fargate.
`make deploy-frontend` builds static assets, syncs private S3 and invalidates CloudFront.
GitHub Actions uses the same targets after all checks pass on main.

This deployment uses CloudFront HTTPS hostnames without purchasing a domain.
The custom-domain / ACM / ALB HTTPS part of the assignment is intentionally omitted.

The older Lambda setup is retained for database continuity; see [historical notes](docs/LEGACY-LAMBDA.md).

## AI agenda suggestions (Lab 6)

Calendar → **Add agenda** opens a manual agenda editor with optional **Paste an
agenda** parsing through Bedrock. Review the marked suggestions and press Save;
only the authenticated main API writes to the database. See [Lab 6 setup](docs/LAB6.md),
[ADR 0006](docs/adr/0006-llm-agenda-parsing.md), and
[the container diagram](docs/ARCHITECTURE.md).

## Infrastructure migration (Lab 7)

Terraform definitions for Cognito, weekly reports and the agenda parser live in
`infra/`. See [migration instructions](docs/LAB7.md) and
[ADR 0007](docs/adr/0007-terraform.md). HCP Terraform owns infrastructure runs;
GitHub Actions continues deploying the application. All 49 Terraform resources were imported without replacing resources;
the three former stacks and templates are retired. Run `make infra-init`,
`make infra-plan`, and `make infra-outputs`; applies run in HCP after review. Submission evidence stays
local under ignored `submission/lab7/`.

## Google Cloud deployment (Lab 9)

Peach also runs on GCP project `peach-lab9-2026` (us-central1):

- Frontend: https://peach-lab9-2026.web.app (Firebase Hosting, static Next.js export)
- API: https://peach-api-u2sij2lmoa-uc.a.run.app (Cloud Run, same FastAPI image, no Mangum)
- Database: Cloud SQL PostgreSQL 16 `db-f1-micro`, 10 GiB SSD; schema created by
  running Alembic migrations on an empty database (no `pg_dump` from Aurora)

Terraform lives in `gcp/` with its own HCP state (`peach-lab7/peach-gcp-dev`);
AWS state in `infra/` (`peach-dev`) is untouched. Decisions: [ADR 0009](docs/adr/0009-gcp-multicloud.md).

**Deploy to GCP** (details in the [Lab 9 runbook](docs/LAB9.md)):

```sh
gcloud auth application-default login            # no JSON keys
terraform -chdir=gcp init && terraform -chdir=gcp apply   # APIs, SAs, SQL, secret, registry
docker buildx build --platform linux/amd64 --target cloudrun --push \
  -t us-central1-docker.pkg.dev/peach-lab9-2026/peach/backend:<tag> backend
# set image=<digest>, enable_migration_job=true -> apply
gcloud run jobs execute peach-migrate --region us-central1 --wait
# set enable_api=true -> apply
bash scripts/gcp/build-frontend.sh               # NEXT_PUBLIC_API_URL = Cloud Run URL
firebase deploy --only hosting --project peach-lab9-2026
```

**Still on AWS:** Cognito sign-in (Firebase URLs added to the callback/logout
lists), the weekly report pipeline (EventBridge, SQS, Lambda, SES) and the
Bedrock agenda parser. GCP meetings are not included in the AWS weekly report.

**Stop / start the database** (Cloud SQL does not pause on its own; storage is
still billed while stopped):

```sh
gcloud sql instances patch peach-postgres --project peach-lab9-2026 --activation-policy=NEVER   # stop
gcloud sql instances patch peach-postgres --project peach-lab9-2026 --activation-policy=ALWAYS  # start
```

**Clean up:** set `deletion_protection=false` in `gcp/terraform.tfvars`, apply,
then `terraform -chdir=gcp destroy` and `firebase hosting:disable --project peach-lab9-2026`.
Costs and evidence: [submission worksheet](docs/LAB9-SUBMISSION.md).
