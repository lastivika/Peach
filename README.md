# Peach

A private task board with Next.js, FastAPI, PostgreSQL and Cognito sign-in.

## Development

Copy `.env.example` to `.env`, configure Cognito values, then run `make up`.
Use `make lint` and `make test`. AWS credentials and `.env` must never be committed.

## AWS deployment

See [AWS lab guide](docs/AWS-LAB.md) for architecture, setup, CI/CD, tradeoffs, rollback and teardown.
`make deploy-backend` builds a SHA-tagged ECR image, migrates and updates ECS Fargate.
`make deploy-frontend` builds static assets, syncs private S3 and invalidates CloudFront.
GitHub Actions uses the same targets after all checks pass on main.

This deployment uses CloudFront HTTPS hostnames without purchasing a domain.
The custom-domain / ACM / ALB HTTPS part of the assignment is intentionally omitted.

The older Lambda setup is retained for database continuity; see [historical notes](docs/LEGACY-LAMBDA.md).
