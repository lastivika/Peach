# Lab 9: confirmed Moodle requirements and evidence plan

Source: [UCU Lab 9, assignment 158424](https://learn.ucu.edu.ua/mod/assign/view.php?id=158424),
read through the owner's authenticated browser on 2026-11-12. This replaces the
provisional checklist. Deadline shown: **19 November 2026, 23:55 Europe/Kyiv**.
Nothing has been submitted, committed or deployed by this work.

## The four required submissions — status 2026-11-15

| Moodle deliverable | Evidence | Status |
| --- | --- | --- |
| Commit/PR with `gcp/` and the service-choice ADR | `gcp/`, [ADR 0009](adr/0009-gcp-multicloud.md) incl. answers (a)–(c) | PR from branch `lab9-gcp` |
| GCP URL: frontend loads, API reads the DB | https://peach-lab9-2026.web.app → Cloud Run; signed-in `GET /api/v1/items` returned 200 (Cloud Run log, 2026-11-14 21:02 UTC) | Done; screenshot of signed-in Items page to attach |
| Part 3 cost table, four profiles, free-tier assumptions | [LAB9-COSTS.md](LAB9-COSTS.md) | Done |
| Screenshots: BigQuery, Looker Studio, OCR | BigQuery job on `usa_names` (170 MB processed) → table `lab9_demo.names_by_decade`; Vision `DOCUMENT_TEXT_DETECTION` result (confidence 0.93) | OCR done; BigQuery + Looker screenshots taken in console |

Extra Part 4 exercises: Dataflow "Cloud Storage Text to BigQuery" template loaded
8 rows into `lab9_demo.meetings_from_gcs` (job `2026-11-15_04_14_21-11581297166368488086`,
1 × e2-small, dedicated `peach-dataflow` worker SA). Lab 6 agenda prompt in
Vertex AI Studio: run in console.

Clean-up after grading: `lab9_demo` dataset, `gs://peach-lab9-2026-dataflow-demo`,
`peach-dataflow` SA, then `terraform -chdir=gcp destroy` and Firebase Hosting disable.

## Four traffic profiles and the cost worksheet

The assignment specifies a 730-hour month, USD on-demand prices, AWS us-east-1
and GCP us-central1, with tax excluded. It does **not** define requests per second,
request duration, response bytes or database I/O on this page. Obtain the Lab 4
workload assumptions or declare explicit estimates before calculating usage costs.

| Required profile                            | Active application hours/month | Cloud SQL hours with the current prepared configuration | Compute + 10 GB SSD baseline, using Moodle's rates | Alternative if manually stopped outside active hours |
| ------------------------------------------- | -----------------------------: | ------------------------------------------------------: | -------------------------------------------------: | ---------------------------------------------------: |
| Nobody uses it                              |                              0 |                                                     730 |                                              $9.37 |                                                $1.70 |
| Class demonstrations: 10 sessions × 2 hours |                             20 |                                                     730 |                                              $9.37 |                                                $1.91 |
| Office hours: 8 hours × 22 days             |                            176 |                                                     730 |                                              $9.37 |                                                $3.55 |
| Busy continuously                           |                            730 |                                                     730 |                                              $9.37 |                                                $9.37 |

These are **database-only**, not completed cloud totals or a current quote.
The reference calculation is `0.0105 × running_hours + 0.17 × 10`.
Moodle dates its rates to 5 November 2026. Recheck current calculator prices before
submission. Backups, storage overhead, API, image storage, logging, egress and
retained AWS integrations are additional. The stopped alternative is a scenario,
not implemented automation; storage continues billing while SQL is stopped.

Peach's current AWS deployment uses **ECS Fargate + ALB**, not just the old
Lambda architecture from the Spry reference. Repository defaults show a
0.25-vCPU / 0.5-GiB task and an Aurora minimum of 0.5 ACU, with pausing opt-in.
Live AWS settings could not be verified because the AWS CLI session expired.
Do not copy the reference's approximately $0.30 idle AWS total into Peach's table.
Check actual desired task count, CPU architecture, ALB hours/LCUs, Aurora floor
and active hours, public IPv4 charges, storage/I/O and CloudFront plan. If desired,
show the legacy Lambda/pausing-Aurora alternative in a **separate** comparison.

Complete this table in both official calculators and retain links or exported
inputs with the submission evidence:

| Cost line                   | Inputs required for all four profiles                         | Prepared GCP choice / AWS counterpart                                         |
| --------------------------- | ------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Frontend/CDN                | Stored GB, transfer GB, applicable free plan/quotas           | Firebase / current S3 + CloudFront                                            |
| API                         | Requests, billed CPU/memory time, concurrency; AWS task hours | Run: 1 vCPU, 0.5 GiB, min 0 / ECS task + ALB                                  |
| Database                    | Running hours, backup size, disk, I/O                         | Cloud SQL baseline above / actual Aurora capacity and storage                 |
| Network                     | User response bytes, public IPs, cross-cloud traffic          | No NAT/connector / existing AWS topology                                      |
| Registry/secrets/logging    | Image GB, secret versions/accesses, ingested logs             | Artifact Registry, Secret Manager, Logging / ECR, Secrets Manager, CloudWatch |
| Retained integrations       | Cognito MAU, optional parser tokens, report/email activity    | AWS costs remain part of the hybrid GCP deployment total                      |
| **Total and cheaper cloud** | Sum each line for 0, 20, 176 and 730 active hours             | **Pending calculator inputs/results; no unsupported winner claimed**          |

Moodle's Cloud Run reference includes 2M requests, 180,000 vCPU-seconds and
360,000 GiB-seconds free monthly, followed by request and active-compute rates.
Apply allowances only if available to this billing account. Active application
hours are **not** automatically billed CPU hours: request duration and concurrency
matter. Firebase, registry, Secret Manager and logs also have distinct allowances.
Do not subtract free trial credits as if they were a permanent discount.

Required discussion: identify the cheaper cloud for each completed profile and
the cost line that decides it. The GCP idle-cost trap is that Cloud Run scales to
zero but Cloud SQL does not; minimum Run instances, storage, and optional managed
workers can add further ongoing cost. Peach's ECS/ALB baseline is another reason
actual deployment details matter more than the generic Spry example.

References: [Google Cloud calculator](https://cloud.google.com/products/calculator),
[AWS calculator](https://calculator.aws/),
[Cloud SQL pricing](https://cloud.google.com/sql/pricing),
[Cloud Run pricing](https://cloud.google.com/run/pricing).

## The three screenshots — exact scope

1. **BigQuery:** run a query over a public dataset; show the query, result, and
   bytes processed. Record the region, cache status and cost cap. A query plan or
   an empty editor is not proof of an executed query.
2. **Looker Studio:** a chart built from that BigQuery result. Show the chart and
   its dimension/metric context. Do not substitute Cloud Monitoring or an app chart.
3. **OCR:** one Document AI processor result **or** one Vision OCR result on a
   synthetic/non-confidential document, receipt or handwritten sample. Show the
   input and extracted text, redact incidental personal information, and record
   the processor/API used. Both OCR products are not required for submission.

These are separate demos; do not add their services to the core application
Terraform just to generate evidence. No queries, processors, paid API calls,
Dataflow jobs or screenshots were produced during this no-deployment stage.
Free allowances do not make unbounded workloads safe to run without a scope.

Part 4 also labels a Gemini agenda-prompt experiment and a small Cloud Storage
Text-to-BigQuery Dataflow job as student exercises, although they are not among
the three requested screenshot deliverables. Record them as pending exercises;
do not silently mark them completed. Veo, enterprise Looker and managed Airflow
are class demonstrations, not infrastructure to provision for this repository.
Part 5 discusses certifications; buying an exam is not one of the four submissions.

## Core requirements mapped to Peach

- The frontend is a real Next.js static export; the existing UI and API calls
  remain. Firebase Hosting emulator checks are separate from a successful login.
- The API is the existing FastAPI app started by Uvicorn on `PORT`, without the
  Lambda handler/adapter in its runtime execution path. Mangum remains installed
  for the preserved AWS image target but is not invoked by Cloud Run.
- PostgreSQL/SQLAlchemy/Alembic retain UUIDs, relationships, ownership, timezone
  data and JSONB agendas. The chosen import path is migrations into an empty DB,
  not a copy of Aurora user data.
- Keeping Cognito, weekly reports and the agenda parser on AWS matches Part 2's
  core scope; migrating those is explicitly stretch work. GCP meetings are not
  silently included in the AWS report database.
- Separate state and service accounts, ADC and prepared HCP WIF match Part 0.
  Firebase callback changes still require an authorized AWS change.
- README/runbook must explain deployment and stopping SQL. After a future deploy,
  inspect costs the following day and record cleanup of demo outputs as well as
  core resources. Terraform cannot remove CLI-created Firebase releases or
  manually created demo outputs it does not manage.
