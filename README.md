# Peach

A web application with a Next.js/React frontend, FastAPI backend, and PostgreSQL database.
The demo board supports creating, editing, moving, and deleting task cards.

## Local development

```sh
# Only if .env does not already exist:
cp .env.example .env
docker compose up -d --build
make lint
make test
```

- Frontend: http://localhost:3000
- API documentation: http://localhost:8000/docs
- Liveness: `/health`; database readiness: `/api/v1/health/ready`.

## AWS lab

Follow **[the assignment guide](docs/AWS-LAB.md)** for account setup, ECS, domains,
OIDC, CI/CD, evidence to submit, rollback and cleanup.

```sh
make deploy-backend    # commit-SHA image -> ECR -> migration -> ECS Fargate + HTTPS ALB
make deploy-frontend   # static export -> private S3 -> CloudFront -> cache invalidation
```

The lab backend template is `infra/ecs-backend.yaml`. It reuses the Aurora database
created by the earlier deployment (`peach-backend`), or an explicitly supplied
Secrets Manager URL secret and database security group in the same VPC.
The database password is injected into ECS from Secrets Manager, never stored in GitHub.

The existing live Lambda deployment has **not** been migrated yet. Its template remains
`infra/backend.yaml`; `make deploy-lambda` is retained for legacy rollback.
See [legacy reference](docs/LEGACY-LAMBDA.md). Do not delete that stack while ECS uses its database.

## Repository map

| Path | Purpose |
| --- | --- |
| `backend/app/` | API routes, schemas, models and database operations |
| `backend/migrations/` | Alembic database schema history |
| `backend/tests/` | pytest API and Lambda adapter tests |
| `frontend/app/` | Dashboard and task-board pages |
| `frontend/components/` | React components and shadcn UI primitives |
| `frontend/tests/` | Vitest component and API-client tests |
| `.github/workflows/` | Checks on every push/PR; deploy on passing main pushes |
| `infra/` | CloudFormation infrastructure templates |
| `scripts/` | Shared local/CI deploy commands and DNS helpers |

## CI/CD

`.github/workflows/deploy-backend.yml` calls the reusable checks in `lint.yml`.
Checks run Ruff, ESLint, Prettier, TypeScript, backend/frontend tests and a static
frontend production build. Only a green `main` run gets an AWS OIDC token and
runs the same Makefile deploy targets used locally. PRs and other branches do not deploy.
GitHub settings and the first ECS bootstrap must be completed before this pipeline can deploy.

The app currently has no authentication. Use demo data only on a public deployment.
