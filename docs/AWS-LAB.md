# AWS deployment assignment

## Current state and remaining evidence

The earlier deployment is Next.js on private S3/CloudFront and FastAPI on Lambda
with Aurora PostgreSQL. That proves public hosting, but Lambda is not the lab's
required ECS backend. The code in this change prepares ECS and CI/CD; it does not
claim an ECS deployment or a successful GitHub Actions run already happened.

The selected repository is `lastivika/Peach`. The Git remote and ignored local
configuration now point to it. A domain/DNS access and a verified non-root AWS
identity are still needed before live completion.

## 1. Local checks and the first red pipeline

Ruff, ESLint and Prettier are already dependencies. Run:

```sh
make lint
make test
```

`make lint` checks Python lint/formatting and frontend lint/formatting. Generated
`frontend/out/` files are excluded from Prettier.

The workflow has:

- `on`: push, pull request, and manual dispatch.
- `jobs`: checks, backend deployment, frontend deployment.
- `needs`: checks must pass before backend, and backend must pass before frontend.
- `runs-on`: the hosted runner executing that job.
- `steps`: ordered actions (`uses`) and commands (`run`).
- `permissions: id-token: write`: only deployment jobs can request an OIDC token.

To demonstrate a real failure safely, use a branch in **your own repository**:

```sh
git switch -c lab/linter-demo
printf 'import os\n' > backend/app/lint_demo.py
git add backend/app/lint_demo.py
git commit -m "lab: demonstrate an unused-import lint failure"
git push -u origin lab/linter-demo
```

Wait for the actual GitHub run to fail with Ruff F401 and save its URL/screenshot.
Then remove only that demonstration file, commit the fix, push, and save the green
run. Do not merge the deliberate error into main. This guide is not evidence that
the red/green exercise has already been performed.

## 2. Stop using root

In AWS Console, enable MFA on the root user, then create your own IAM user with
the lab's required permissions. Complete passwords, MFA and key creation yourself.
Use that IAM identity for deployment; the new backend script rejects a root ARN.

If your course explicitly requires CLI access keys, configure them locally:

```sh
aws configure --profile peach-lab
aws sts get-caller-identity --profile peach-lab
```

Type the access key and secret only into the local terminal prompts. They belong
in the AWS CLI credential store, not `.env`, source files, screenshots or chat.
Use `AWS_PROFILE=peach-lab` in your ignored `.env`. A browser-based non-root
`aws login --profile peach-lab --region us-east-1` is an alternative if your teacher permits it.
Never create root access keys. GitHub uses OIDC, regardless of your local login method.

## 3. Domains and certificates

Choose `api.YOUR_DOMAIN` and `app.YOUR_DOMAIN` and set these **non-secret** values in `.env`:

```dotenv
AWS_PROFILE=peach-lab
AWS_REGION=us-east-1
PROJECT_NAME=peach
DATABASE_STACK_NAME=peach-backend
API_DOMAIN_NAME=api.YOUR_DOMAIN
API_CORS_ORIGINS=https://app.YOUR_DOMAIN
DOMAIN_NAME=app.YOUR_DOMAIN
GITHUB_REPO=YOUR_GITHUB_USER/YOUR_REPOSITORY
```

Do not paste the placeholders unchanged. Your existing ignored `.env` also holds
local Docker settings; leave those intact.

```sh
make cert-api
```

This requests an ACM certificate in `AWS_REGION`, prints the validation CNAME and
saves its ARN as `API_CERTIFICATE_ARN`. Add the exact CNAME name/value at your DNS
provider and wait for the ACM status to become `ISSUED`. Keep the validation record
for renewal. `make deploy-backend` refuses an unissued certificate.

For frontend HTTPS, use the existing helper:

```sh
make domain DOMAIN=app.YOUR_DOMAIN
```

The CloudFront certificate must be in `us-east-1`; the ALB certificate must be in
the ALB's region. The frontend helper prints the required DNS records or manages
them when it finds a matching public Route 53 zone.

A **validation CNAME** proves domain ownership to ACM. A separate **routing CNAME**
points `api` to the ALB's DNS name, or `app` to CloudFront. They are not interchangeable.
If your API zone is in Route 53, set `API_HOSTED_ZONE_ID` so CloudFormation creates
the API alias. Otherwise add the ALB routing CNAME manually when deployment prints
its hostname, then rerun the deploy to complete verification. Do not proxy the API
through an unrelated CDN while validating the lab's direct ALB route.

```sh
dig +short api.YOUR_DOMAIN
dig +short app.YOUR_DOMAIN
curl -I http://api.YOUR_DOMAIN/health
curl https://api.YOUR_DOMAIN/api/v1/health/ready
```

HTTP should redirect to HTTPS; HTTPS readiness should return both statuses as `ok`.

## 4. First ECS deployment

The current Aurora database is deliberately reused. Its existing Lambda stack
remains until the migration is verified. No database is copied or deleted.
For a separately managed database, supply `DATABASE_URL_SECRET_ARN`,
`DATABASE_SECURITY_GROUP_ID`, `AWS_VPC_ID`, and `AWS_SUBNET_IDS` explicitly.
The database and ECS tasks must be in the same VPC. The secret must contain a
complete `postgresql+asyncpg://...` URL; use an AWS-managed Secrets Manager key
or extend the execution role for your customer-managed KMS key.

Select public subnets in at least two AZs with Internet Gateway routes. The
script can discover default subnets in the database VPC. Fargate uses public IPs
for ECR/Secrets Manager egress, but its security group admits port 8000 only from
the ALB. This lab avoids a NAT gateway; a production private-subnet design would
need NAT or appropriate VPC endpoints.

Commit the backend code before deploying. Then, using your non-root bootstrap identity:

```sh
make deploy-backend
make deploy-frontend
```

The backend target:

1. Builds the Docker `runtime` target for ARM64 and pushes an immutable full-SHA
   tag to `peach-ecs-backend` in ECR. Existing SHA images are reused.
2. Creates/updates `peach-ecs-backend` CloudFormation resources: ECS cluster,
   task definition, Fargate service, ALB/target group, HTTPS listener and port-80 redirect.
3. Keeps the old service release while running `alembic upgrade head` in one task.
4. Promotes the new task definition only if the migration exits successfully.
5. Waits for stability and checks DNS, HTTPS and database readiness.
6. Saves `BACKEND_URL` for the frontend build.

New infrastructure is initially created with zero API replicas until migrations
succeed. Failed migration tasks leave the old service release in place. Database
migrations must be backward-compatible with the previous application version.
The ECS deployment circuit breaker rolls back failed application rollouts; it
cannot undo a database migration. Prior task definitions are retained for rollback.

The frontend target builds the static export, uploads immutable hashed assets,
then HTML/other files, and invalidates CloudFront. The S3 bucket stays private.

## 5. GitHub OIDC and deployment

Bootstrap ECS locally first. The CI role deliberately cannot create arbitrary IAM
roles, grant itself permissions, create the initial ECR repository, or rebuild the
entire account infrastructure. Infrastructure/security changes require your
non-root bootstrap identity and review.

Set `GITHUB_REPO` to your own repository before running:

```sh
make github-role
```

The trust policy permits only:

```text
aud = sts.amazonaws.com
sub = repo:YOUR_GITHUB_USER/YOUR_REPOSITORY:ref:refs/heads/main
```

No wildcard repository or branch is trusted. PRs and fork branches cannot assume
the role. Anyone who can change trusted main workflows is still powerful: protect
main and review workflow changes. OIDC credentials expire, but credentials stolen
while valid can still be abused within their permissions.

Set these GitHub **Actions variables**, not access-key secrets:

| Variable | Value |
| --- | --- |
| `AWS_DEPLOY_ROLE_ARN` | Output from `make github-role` |
| `AWS_REGION` | `us-east-1` |
| `PROJECT_NAME` | `peach` |
| `API_DOMAIN_NAME` | Your API domain |
| `API_CERTIFICATE_ARN` | Issued regional ACM ARN |
| `API_CORS_ORIGINS` | `https://app.YOUR_DOMAIN` |
| `API_HOSTED_ZONE_ID` | Optional public Route 53 zone ID |
| `AWS_VPC_ID`, `AWS_SUBNET_IDS` | Optional explicit networking configuration |
| `DATABASE_STACK_NAME` | `peach-backend` unless using another existing stack |

For an external database also set its secret ARN and security group variables.
These identifiers are not passwords. The execution role reads the actual database
secret at task startup; GitHub does not receive the database password.

Every push runs CI. Only green main pushes deploy the exact checked commit via
`make deploy-backend`, then `make deploy-frontend`. The old commit-message
`deploy` trigger has been removed. Save the real green deployment run URL and
show that the running ECS image tag matches that commit's full SHA.

## 6. Rollback and resource inventory

To redeploy an image that already exists in ECR:

```sh
IMAGE_TAG=FULL_PREVIOUS_40_CHARACTER_SHA make deploy-backend
```

This restores application code, not the old database schema or frontend bundle.
Choose a version compatible with current migrations. Redeploy matching frontend
source separately when needed.

Expected inventory after the lab:

- `peach-ecs-backend`: ALB, listeners, target group, ECS cluster/service,
  Fargate tasks, task IAM roles, security groups and CloudWatch log group.
- `peach-frontend`: private S3 bucket and CloudFront distribution/function.
- `peach-backend`: original Aurora database, secret and legacy Lambda resources.
- `peach-github-oidc`: GitHub deploy role and optionally an OIDC provider.
- ECR repositories `peach-ecs-backend` and legacy `peach-backend`.
- ACM certificates and DNS records; retained ECS task-definition revisions.

ALB, Fargate, public IPv4 addresses and database/storage resources can incur
charges. Do not assume this architecture is free. Create an AWS budget alert and
check billing during the lab. Alerts notify; they do not automatically stop spending.
The board's open dashboard polls the database every 15 seconds and can prevent
Aurora from staying idle. Close it when not demonstrating the application.

After submission, teardown is deliberate and requires confirmation:

```sh
make destroy-backend   # ECS + ALB; retains database and ECR images
make destroy-frontend  # frontend bucket/distribution
make destroy-database # legacy Lambda + Aurora; permanently deletes database data
```

Delete ECS first: its database ingress rule references the old database security
group. Export anything you need before deleting the database. Then remove remaining
ECR images/repositories, unused certificates/DNS, the OIDC role stack and any
unneeded retained task definitions/provider. Verify the resource inventory and
billing dashboard rather than assuming one delete command removes everything.

## Discussion answers

- **Why CloudFront?** HTTPS, a certificate/custom domain, edge caching and access to
  a private S3 origin. S3 website hosting alone does not provide the same setup.
- **ECR vs ECS?** ECR stores versioned container images. ECS schedules and maintains
  running tasks using those images; Fargate provides their compute.
- **Health checks?** ALB and container probes use `/health` for process liveness.
  ECS replaces unhealthy tasks; ALB normally excludes unhealthy targets. If all
  targets are unhealthy, ALB can fail open, so probes do not guarantee successful
  traffic. `/api/v1/health/ready` separately tests the DB with `SELECT 1` during
  deployment. A shared DB outage should not trigger mass container restarts.
- **Two CNAMEs?** ACM validation proves ownership; routing sends application
  traffic to the correct ALB or CloudFront hostname.
- **Leaked keys vs OIDC?** Long-lived keys work until revoked, from anywhere.
  OIDC requires a trusted repository/branch token to obtain temporary credentials.
  A compromised trusted workflow is still dangerous; short-lived does not mean harmless.
- **At 1,000 organisations?** Keep ECR, ECS/Fargate, ALB, private S3/CloudFront and
  OIDC. First fix the app's lack of authentication, tenant isolation and access
  control. Then measure load: one 0.25-vCPU/512-MB task and the small shared database
  are likely capacity limits, but organisation count alone does not determine the
  first bottleneck. Add replicas/autoscaling, DB sizing/pooling, observability and
  tested backups based on measurements. Avoid creating an ALB per organisation.

## Submission checklist

- [ ] Root MFA and non-root CLI identity demonstrated without showing credentials.
- [ ] Local lint/test results.
- [ ] Real failing lint commit/run and subsequent fixed green run.
- [ ] Public custom frontend/API domains with valid HTTPS and HTTP redirect.
- [ ] ECS task image tag matches a main commit SHA.
- [ ] Main push automatically deployed after checks passed.
- [ ] OIDC trust policy explained and no long-lived keys in repository secrets.
- [ ] Resource inventory, costs reviewed, and teardown completed after grading.

References: [ECS service](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ecs-service.html),
[GitHub OIDC with AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws),
[ALB health checks](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html).
