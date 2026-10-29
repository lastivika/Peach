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
