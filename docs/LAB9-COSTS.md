# Lab 9 Part 3: Peach cost table, AWS vs GCP

USD on-demand list prices, AWS us-east-1 vs GCP us-central1, 730-hour month,
tax excluded, free trial credits **not** subtracted. GCP prices are from the lab
brief (5 Nov 2026); AWS prices are the us-east-1 list prices used in the AWS
calculator. Sizing is read from the live deployments on 2026-11-15.

## Traffic assumptions (Lab 4 defined only active hours)

| Assumption                   | Value                                          |
| ---------------------------- | ---------------------------------------------- |
| Users online while active    | 5 (team + instructor)                          |
| API requests per active hour | 300 (≈ 1 action per user per minute)           |
| Server time per request      | 200 ms on 1 vCPU / 0.5 GiB                     |
| Response size                | 5 KB JSON; static pages come from the CDN      |
| Active hours / month         | nobody 0 · demos 20 · office hours 176 · busy 730 |

Busy month = 219,000 requests, 43,800 vCPU-s, 21,900 GiB-s, ~1.1 GB API egress.

## Free-tier assumptions

- **Cloud Run:** 2M requests, 180,000 vCPU-s, 360,000 GiB-s per month. Even the busy
  profile uses ≈ 11 % / 24 % / 6 % of these → $0.
- **Firebase Hosting:** 10 GB stored, 360 MB/day transfer. Our build is 2.16 MB → $0.
- **Artifact Registry:** 0.5 GB free; repository is 102 MB → $0.
- **Secret Manager:** 6 active versions + 10,000 accesses free; we use 1 version → $0.
- **Cloud Logging:** 50 GiB/month free → $0. **Egress:** ≈ 1 GB → ≈ $0.
- **AWS:** CloudFront always-free tier (1 TB, 10M requests), Cognito Lite free up to
  10,000 MAU, Lambda 1M requests free — these are also used by the GCP deployment,
  which keeps Cognito on AWS.
- Free tiers are per billing account and shared with other projects.

## Table 1: Peach exactly as deployed today

Neither deployment scales its database or load balancer with usage, so every
profile costs the same.

| Line                    | AWS (ECS Fargate + ALB + Aurora Serverless v2)       | AWS $/mo  | GCP (Cloud Run + Cloud SQL + Firebase)       | GCP $/mo |
| ----------------------- | ---------------------------------------------------- | --------: | -------------------------------------------- | -------: |
| Frontend / CDN          | S3 + CloudFront (free tier)                          | 0.00      | Firebase Hosting (free quota)                | 0.00     |
| API compute             | 1 ARM task, 0.25 vCPU / 0.5 GB, 730 h                | 7.21      | Cloud Run, min 0, inside free tier           | 0.00     |
| Load balancer           | ALB 730 h × $0.0225 (LCUs ≈ 0)                       | 16.43     | none (Cloud Run has its own HTTPS URL)       | 0.00     |
| Public IPv4             | 3 addresses × $0.005/h (2 ALB + 1 task)              | 10.95     | none billed                                  | 0.00     |
| Database compute        | Aurora min 0.5 ACU × $0.12/h × 730, never pauses     | 43.80     | Cloud SQL db-f1-micro $0.0105/h × 730        | 7.67     |
| Database storage        | Aurora 1 GB × $0.10                                  | 0.10      | 10 GB SSD × $0.17                            | 1.70     |
| Secrets                 | Secrets Manager 1 secret                             | 0.40      | Secret Manager (free)                        | 0.00     |
| Registry / logs         | ECR, CloudWatch (≈ 0)                                | 0.10      | Artifact Registry, Logging (free)            | 0.00     |
| Retained AWS pieces     | —                                                    | —         | Cognito, parser, reports on AWS (free tier)  | 0.00     |
| **Total, every profile** |                                                     | **≈ 78.99** |                                            | **≈ 9.37** |

**Cheaper: GCP in all four profiles.** The deciding line is the database floor:
Aurora's 0.5 ACU minimum costs $43.80 vs $7.67 for db-f1-micro. The ALB and its
public IPv4 addresses ($27.38) are the second-biggest difference. Cloud Run at
min 0 with this traffic stays inside the free tier.

## Table 2: same app if both clouds scaled with use

AWS uses the Lab 4 serverless layout (Lambda + function URL, Aurora min 0 ACU with
auto-pause, no ALB). GCP stops Cloud SQL outside active hours
(`--activation-policy=NEVER`); its SSD storage is still billed. Aurora is
counted at 0.5 ACU while active.

| Profile                       | Active h | AWS: Aurora 0.5 ACU × h × $0.12 + $0.10 storage + $0.40 secret | GCP: $0.0105 × h + $1.70 storage | Cheaper | Deciding line                                       |
| ----------------------------- | -------: | -------------------------------------------------------------: | -------------------------------: | ------- | --------------------------------------------------- |
| Nobody uses it                | 0        | **0.50**                                                       | 1.70                             | AWS     | GCP pays for 10 GB SSD even when stopped; Aurora paused |
| Class demos (10 × 2 h)        | 20       | **1.70**                                                       | 1.91                             | AWS (barely) | Same: storage floor vs cheap active Aurora hours  |
| Office hours (8 h × 22 days)  | 176      | 11.06                                                          | **3.55**                         | GCP     | Aurora $0.06/h vs Cloud SQL $0.0105/h                 |
| Busy 24/7                     | 730      | 44.30                                                          | **9.37**                         | GCP     | Same: database hourly rate                           |

Lambda and Cloud Run stay inside their free tiers at this traffic in every profile.

## The idle-cost traps

- **AWS ("Aurora kept awake"):** our live Aurora has `MinCapacity 0.5`, so it never
  pauses — $43.80/month even with zero users. Peach's AWS deployment also keeps an
  ECS task, an ALB and 3 public IPv4 addresses running all month.
- **GCP equivalent:** **Cloud SQL has no auto-pause at all.** Cloud Run scales to
  zero, but the database bills $7.67/month of compute until someone stops it by
  hand, and the 10 GB SSD ($1.70) is billed even while stopped. Setting Cloud Run
  `min_instance_count > 0` would be a second always-on cost. Firestore would make
  idle cost $0 but needs a rewrite away from SQL (ADR 0009).
- Budget alerts ($5, 50/90/100 %) only warn; they do not stop either cloud.

Calculators: [AWS](https://calculator.aws/), [Google Cloud](https://cloud.google.com/products/calculator).
