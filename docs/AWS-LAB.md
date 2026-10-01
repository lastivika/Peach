# AWS lab

## Architecture and deliberate domain exception

This lab uses AWS-issued hostnames; no domain was purchased at the owner's request.
The frontend is a static Next.js export in private S3 behind CloudFront OAC.
The API uses CloudFront HTTPS -> ALB HTTP -> ECS Fargate -> existing Aurora PostgreSQL.
ALB ingress is limited to AWS's managed CloudFront origin-facing prefix list;
containers only accept the ALB security group. The origin leg is HTTP: this does
not satisfy the assignment's custom-domain ACM certificate and ALB HTTPS listener
step. Viewer HTTPS and HTTP-to-HTTPS redirects are provided by CloudFront.
The API distribution disables caching and forwards authorization and query strings.

Cognito hosted login uses authorization code + PKCE, state and nonce, with email
verification. Tokens are stored only in sessionStorage; no refresh tokens are
persisted. Sign in again when the one-hour token expires. The API validates JWT
signature, issuer, audience, expiry, token use and verified email. Queries enforce
ownership; another user's item returns 404. Existing legacy items are preserved
with no owner and do not appear in a new user's board.

## Reproduce deployment

1. `aws login --profile peach-lab`; put `AWS_PROFILE=peach-lab` in ignored `.env`.
2. Bootstrap Cognito: deploy `infra/cognito.yaml` with ProjectName and SiteUrl.
3. Set `API_CORS_ORIGINS` to the frontend HTTPS origin.
4. Commit backend changes, then `make deploy-backend`.
5. `make deploy-frontend` (optionally `FRONTEND_BUILD_DOCKER=1` for Docker builds).
6. `make github-role`, then set repository variables `AWS_DEPLOY_ROLE_ARN`,
   `AWS_REGION=us-east-1`, `API_CORS_ORIGINS`.
7. Push to `main`. CI runs Ruff, ESLint, Prettier, tests, template checks and a
   production build before running those same two Makefile deployment targets.

Images use full commit SHA tags and ECR tag immutability. A single migration task
must exit successfully before the service is promoted. The service uses a deployment
circuit breaker. Rollback: set IMAGE_TAG to an existing known-good SHA and run
`make deploy-backend`; database schema must remain compatible.

OIDC trust requires audience `sts.amazonaws.com` and exactly
`repo:lastivika@102419987/Peach@1399359780:ref:refs/heads/main`. No AWS access keys belong in GitHub secrets.
CI can pass only the two ECS task roles; infrastructure bootstrap uses the personal
IAM administrator. An unrelated repository or branch cannot assume the deploy role.

## Class discussion

- CloudFront adds edge delivery and viewer HTTPS; the S3 bucket stays private.
- ECR stores immutable images; ECS schedules and replaces running containers.
- `/health` tests process liveness; `/api/v1/health/ready` checks `SELECT 1` against
  the database. ALB removes unhealthy targets; ECS replaces unhealthy tasks.
- An ACM validation CNAME proves domain control; a routing CNAME directs traffic.
  Custom-domain validation is deliberately omitted in this deployment.
- A leaked access key works until revoked. OIDC credentials expire and obtaining
  them requires a token matching the repository/main trust policy.
- At 1,000 organisations retain S3/CloudFront/ECR/ECS/OIDC, add explicit tenancy,
  pagination and indexing, autoscaling and database connection management. The
  single small task and database capacity need measurement and scaling first.

## Costs and teardown

This is an active paid AWS project. Fargate, ALB, Aurora, logs and public IPv4 can
incur costs even with no visitors. No NAT gateway is created. After grading:
`make destroy-backend` removes ECS, ALB and its API CloudFront distribution;
`make destroy-frontend` removes frontend hosting. `make destroy-database` deletes
the legacy stack and database data: back up needed data first. Cognito's user pool
and historical task definitions are retained; remove them explicitly only when no
longer needed. Delete unused ECR images/repositories and the GitHub OIDC role/provider
only after confirming no other workload uses them.

## CI evidence

- Green checks before the demonstration: https://github.com/lastivika/Peach/actions/runs/36833755064
- Intentional red Ruff run (unused import): https://github.com/lastivika/Peach/actions/runs/36833972218

The retired Lambda URL requires AWS IAM authentication; it is no longer a public
route to the database. The database stack remains because it owns Aurora.
