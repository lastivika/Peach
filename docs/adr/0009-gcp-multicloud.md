# ADR 0009: Prepare Peach for two clouds

Date: 2026-11-12 (Europe/Kyiv)
Status: Accepted for preparation; deployment and cloud verification pending.

## Context and audit

The assignment calls its application Spry; this repository is Peach. The active
checkout has a Next.js 16 App Router UI, FastAPI, SQLAlchemy/asyncpg, Alembic and
PostgreSQL. There is no Redis, Celery, mandatory queue consumer, or server-side
session service in the core request path. No production data is needed for a lab.

`frontend/next.config.ts` already supports `NEXT_OUTPUT=export`. All application
data is fetched by browser React Query hooks; authentication uses
`oidc-client-ts`, authorization code with PKCE, and browser session storage.
Routes are fixed (`/`, `/login`, `/callback`, `/auth/callback`, `/home`, `/items`,
`/calendar`); there are no dynamic URL segments, server actions, API routes,
cookie-dependent SSR, or runtime Next image optimization requirements. Static
HTML contains the application shell, not users' task data. Firebase clean URLs
serve the exported HTML, with explicit rewrites for trailing-slash login and
callback URLs. No catch-all SPA rewrite conceals missing pages. Google fonts are
fetched at build time and require build-time network access.

FastAPI validates Cognito ID-token signature, issuer, audience, expiry and token
use, then resolves `cognito_sub` to the local user. Item, meeting and agenda
operations enforce owner scope. `/health` is public liveness;
`/api/v1/health/ready` is the existing public database probe, returning no data or
connection details. The core backend does not invoke AWS APIs with AWS credentials;
Cognito JWKS discovery uses public HTTPS. Retain this behavior on Cloud Run.

PostgreSQL features include UUIDs, foreign keys, transactions, timezone-aware
meeting timestamps and JSONB agenda/suggestion payloads. Migrations `0001` through
`0005` establish these tables and preserve owner isolation. Existing AWS runtime
startup invokes Alembic; the new `cloudrun` Docker target has its own startup
command without migrations. The private migration job runs the same image digest
and `alembic upgrade head` exactly when an operator executes it.

## Component decisions

| Existing Peach component                                    | GCP deployment                                    | Decision / reason                                                             |
| ----------------------------------------------------------- | ------------------------------------------------- | ----------------------------------------------------------------------------- |
| S3 + CloudFront frontend                                    | Firebase Hosting static export                    | Migrate hosting; same UI and browser API calls                                |
| ECS Fargate API; historical Lambda                          | Cloud Run service                                 | Migrate execution, preserve JWT and owner checks                              |
| ECR backend image                                           | Artifact Registry                                 | Separate registry, linux/amd64 image, digest pinned                           |
| Aurora PostgreSQL                                           | Cloud SQL PostgreSQL 16                           | New empty relational DB; no AWS data copy                                     |
| Secrets Manager DB URL                                      | Secret Manager version                            | API/job identities read only the specific secret                              |
| Cognito + Google federation                                 | Existing AWS Cognito                              | Retain identity and user subjects; no user migration                          |
| Agenda parser Lambda + Bedrock                              | Browser calls existing AWS URL                    | Retain optional integration; approved CORS update needed                      |
| EventBridge/Scheduler, SQS, report Lambdas, S3 reports, SES | No GCP deployment of report pipeline              | Existing AWS pipeline remains tied to AWS database; GCP meetings are excluded |
| CloudWatch application logs                                 | Cloud Logging for Cloud Run                       | Structured service/job logs; never log tokens or DB URLs                      |
| HCP `peach-lab7/peach-dev`                                  | HCP `peach-lab7/peach-gcp-dev`                    | Separate state, working directory, credentials and IAM                        |
| AWS VPC/ALB/security groups                                 | Cloud Run ingress + Cloud SQL authenticated proxy | No GCP VPC connector, NAT, load balancer, or VPN needed                       |

Firestore would require rewriting relational queries, ownership joins and
migrations, so it is rejected. Cloud SQL Enterprise `db-f1-micro`, one zone,
10 GiB SSD and two retained automated backups are suitable for a low-traffic lab,
not a production availability target. No HA, replicas, PITR or automatic storage
growth. Monitor disk usage; fixed storage can fill. PostgreSQL 16 avoids choosing
an already end-of-life database version.

The Cloud SQL instance has public IPv4 but **no authorized networks**. Cloud Run's
Cloud SQL integration provides an authenticated encrypted proxy and Unix socket;
`roles/cloudsql.client` and DB credentials are both needed. No `0.0.0.0/0` database
allowlist exists. The proxy connection avoids the fixed cost of a serverless VPC
connector/NAT. Runtime outbound HTTPS can reach Cognito. Public service invocation
is necessary for browser Cognito tokens; Google IAM does not validate these tokens.
Only the transport is public: protected application endpoints retain their
existing authorization. Migration jobs have no public invoker binding.

API and migration use separate service accounts, each with only Cloud SQL client
and access to the DB URL secret. They currently share a DB schema-owner user to
match the application's existing migration model; a production follow-up should
separate DDL and DML database roles. One API instance, concurrency eight and no
persistent pool reduce connection pressure on the shared-core database. Scaling
limits are not a hard spending cap and rollouts can transiently exceed them.

## Credentials, state and deployment sequencing

Use local ADC for bootstrap, while the dedicated HCP workspace is in Local
execution mode. Its state remains remote. The optional HCP workload identity
provider restricts trust to the organization, workspace name and immutable
workspace ID. Switch to Remote mode only after federation exists. No long-lived
GCP service account key, AWS key or Terraform remote-state reference is needed.
The infrastructure manager has project administration roles necessary to manage
these resources; it must never be used by the API. Restrict workspace applies,
variables, state reads and VCS branches accordingly.

The generated DB password and Secret Manager payload **are in Terraform state**.
Sensitive flags only redact output. Do not export state or saved plans to shared
locations or Git. Secret versions are pinned in workloads; rotation requires a
coordinated DB password update and job/service rollout. This lab is not designed
for zero-downtime password rotation. Migration execution is deliberately not a
Terraform provisioner: successful creation of a job does not prove a successful
migration. Deployment uses foundation, image/job, migration, API, frontend stages.

## Required answers (Lab 9 Part 1)

**(a) Database.** Chosen: Cloud SQL PostgreSQL `db-f1-micro`, running 24/7 while
the lab is graded, stopped by hand (`--activation-policy=NEVER`) otherwise.

| Option                         | Latency                                   | Bill (730 h)                          | Code change                          |
| ------------------------------ | ----------------------------------------- | ------------------------------------- | ------------------------------------ |
| Cloud SQL 24/7 (chosen)        | Same region as Cloud Run, ~1 ms           | $9.37                                 | None (same SQLAlchemy/Alembic)       |
| Cloud SQL stopped at night     | Same; first request after start fails until the DB is up (minutes) | $1.70 storage + $0.0105/h running | None; needs a manual or scheduled start/stop |
| Firestore                      | Low, but per-document reads              | ≈ $0 idle, per-operation              | Rewrite models, queries, ownership joins, migrations |
| Keep Aurora on AWS, cross-cloud | us-central1 → us-east-1 ≈ 20–30 ms per query, several per request | Aurora floor $43.80 + AWS egress, plus opening Aurora to the internet | None in code, but a public DB endpoint and TLS/allow-list work |

**(b) E-mail.** GCP has no SES equivalent. Weekly report e-mail stays on **AWS SES**,
sent by the existing AWS report workers (IAM role, no API key). If GCP ever sends
e-mail itself, use **SendGrid**: its API key goes in **Secret Manager** as
`peach-sendgrid-api-key`, readable only by a dedicated sender service account, and
mounted into that one Cloud Run job — never in `NEXT_PUBLIC_*`, Terraform outputs
or Git.

**(c) Not moved, and why.**

- **Cognito → Identity Platform:** moving would change every user's `sub`, which is
  the owner key on all tasks and meetings; keeping Cognito lets both clouds share
  one login and needs only extra callback URLs.
- **Weekly report pipeline (EventBridge, SQS, report Lambdas, S3, SES):** it reads
  the AWS database; porting it means Cloud Scheduler + Pub/Sub + a new e-mail
  provider for no user-visible gain in this lab.
- **Agenda parser (Lambda + Bedrock):** Vertex AI would need prompt re-validation,
  and the trial credit does not cover Claude partner models; the browser keeps
  calling the AWS parser (optional feature).
- **CloudWatch dashboards and AWS-specific Terraform:** replaced only where the core
  path needs it (Cloud Logging for Cloud Run).

## Consequences and remaining integrations

Cognito currently allows only the AWS site and localhost. Firebase login/logout
requires adding the Firebase callback and logout URLs **while retaining the old
ones**, through a separately reviewed AWS change. GCP Terraform does not manage
Cognito. Google federation continues to redirect through the existing Cognito
domain; the Google OAuth provider client need not switch to Firebase Auth.
The parser's function URL CORS also currently allows only the AWS site. Until its
origin list is approved and updated, omit its frontend URL: the existing UI
reports AI unavailability, and manual agenda editing remains real and usable.

Email delivery is not part of core CRUD or manual agendas. Cognito's existing
account-email behavior remains on AWS. SES has no direct built-in Cloud Run
transactional email counterpart. Sending GCP reports would need a separately
scoped worker, queue/scheduler, storage, authenticated delivery integration and
explicit data boundary; it is excluded rather than silently querying AWS data.
No credentials are added to Cloud Run to imitate the AWS report workers.

GCP API and DB are colocated in us-central1 for the lab cost baseline. Ukrainian
users incur transatlantic latency; Firebase CDN reduces static delivery latency,
not API round trips. Cognito key retrieval and optional parser calls remain
cross-cloud dependencies. Existing keys are cached by the application library;
AWS outages can still prevent new sign-ins or AI suggestions. The two deployments
share identities but do not synchronize task/meeting records.

SQLAlchemy, PostgreSQL, OCI images and static frontend files preserve portability.
Cognito tokens, Bedrock, Cloud SQL sockets, Secret Manager and provider-specific
Terraform create vendor coupling. Operating two clouds also adds IAM, logging,
state, release sequencing and troubleshooting overhead. This is an explicit lab
tradeoff, not a claim that multi-cloud automatically gives failover.

Cloud SQL is always billed while running; this architecture will exceed a $5
monthly alert for a full month. Alerts do not stop spending. Prefer a short,
approved demonstration window followed by cleanup. See the runbook for estimate,
validation and evidence requirements.

## References

- [Cloud Run with Cloud SQL PostgreSQL](https://cloud.google.com/sql/docs/postgres/connect-run)
- [Cloud SQL pricing](https://cloud.google.com/sql/pricing)
- [Firebase Hosting routing](https://firebase.google.com/docs/hosting/full-config)
- [HCP GCP dynamic credentials](https://developer.hashicorp.com/terraform/cloud-docs/dynamic-provider-credentials/gcp-configuration)
- Local Next.js installed documentation: `frontend/node_modules/next/dist/docs/01-app/02-guides/static-exports.md`.
