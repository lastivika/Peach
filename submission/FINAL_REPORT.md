# Peach Weekly Meetings Report — Final Report

## Objective

Generate a weekly CSV report from Peach meeting data, store it privately in Amazon S3, and email it after object creation.

## Architecture and flow

Amazon EventBridge Scheduler sends a scheduled request to an Amazon SQS queue. The queue event source mapping invokes the worker Lambda, which queries PostgreSQL, creates a CSV, and writes it to S3 under `reports/{ISO-week}/weekly-meetings.csv`. S3 Object Created events flow through EventBridge to the delivery Lambda, which reads the CSV and uses Amazon SES to send an email with an attachment and a time-limited private link.

The permanent Scheduler and SQS event source mapping are currently disabled. The S3 EventBridge notification and Object Created rule are configured and enabled.

## Implemented components

- PostgreSQL meeting model and Alembic migration `0004` (already applied to production).
- Worker Lambda and delivery Lambda using ARM64 container images.
- SQS retry and redrive configuration, S3 Object Created routing, and SES delivery code.
- Local worker idempotency protection using existing-key checks and conditional `IfNoneMatch="*"` writes.
- Delivery handler accepts native EventBridge S3 events and legacy Records-wrapped event formats.

## Test results

The original controlled runs created the `2026-W41` and `2026-W42` CSV files (288 bytes each) and invoked delivery. SES aggregate statistics showed two delivery attempts and no bounces/rejects/complaints in the corresponding 15-minute interval; inbox delivery was not independently verified.

On 2026-10-15, the marker-enabled ARM64 image was deployed to both Lambdas through a CloudFormation change set that changed only their image digests. One duplicate `2026-W41` SQS request logged `trigger=sqs origin=manual` and `already_exists`; the S3 object remained 288 bytes with its original timestamp. A temporary one-minute schedule emitted a real `source=schedule` message for the same existing week, which logged `trigger=schedule outcome=queued` and `already_exists`. The schedule and production event source mapping were restored to `DISABLED`.

The delivery Lambda logged `trigger=s3 outcome=received` for a single synthetic EventBridge-shaped event referencing an absent `2026-W44` key. It then logged `trigger=s3 outcome=failed` because S3 denied `GetObject` for the missing key; no SES call was reached. This verified the deployed S3 marker without sending a duplicate email. The prior real S3-to-delivery path succeeded on the earlier image, but `accepted_by_ses` has not been reverified on the new image.

An isolated queue test produced three expected `AccessDenied` failures, moved one message to its own DLQ, then completed an SQS redrive. The post-redrive test Lambda invocation ended without an error and both isolated queues were empty. The isolated Lambda, mapping, queues, role/policy, and log group have since been removed; the production DLQ was not read or modified.

After setting both handler loggers to INFO, local verification passed: 16 weekly-report handler tests, Ruff, and `git diff --check`. No production database migration or report generation was run during this continuation.

## Error handling and duplicate behavior

The worker queue retries failed requests and sends messages to a DLQ after the configured receive count. The local worker code skips an existing report and conditionally writes new objects, preventing a repeated SQS request from replacing the report. Delivery has no deduplication store: replaying the same S3 event can send another email. A production duplicate-week experiment remains outstanding.

## Current limitations

- The deployed digest is `sha256:e050a7b5479dd8ebcfa33a8f3bb5db6a90388dc636935ea3b81d8f540c565fef`, tag `weekly-report-step7-markers-20261015T092619Z-local`; both functions are Active on ARM64 with their expected handler commands.
- `trigger=sqs`, `trigger=schedule`, and `trigger=s3` receipt/failure markers are present in CloudWatch. A successful `trigger=s3 outcome=accepted_by_ses` log on the new image was not tested to avoid sending another email.
- The permanent schedule remains disabled on its weekly cron and now carries `{"source":"schedule"}` as in the local template. CloudFormation's resource-drift probe reported `WeeklySchedule=DELETED`, while Scheduler `GetSchedule` confirms the schedule exists in `peach-weekly-reports` with the expected settings; that status discrepancy is unresolved.
- SES remains in sandbox; aggregate statistics are not proof of inbox receipt.
- The tested backend logging fix is pushed to `main` as [8b55cd3](https://github.com/lastivika/Peach/commit/8b55cd3). The unrelated `frontend/.prettierignore` change and this submission-document refresh remain local and uncommitted.

## Temporary resource cleanup

The Step 7-only Lambda, event source mapping, source/DLQ queues, inline policy and role, and log group were deleted after verifying the isolated queues were empty. The production Report DLQ was not read, changed, or redriven. The temporary Docker config holding ECR credentials was also removed.

## Conclusion

The worker, duplicate-week skip, actual scheduled dispatch, trigger markers, retry/redrive, cleanup, and the earlier report delivery path have evidence. The lab is ready for submission with one documented limitation: delivery on the newly deployed image was exercised only up to the S3 read (the safe missing-key test), so a new SES acceptance marker and inbox receipt are not claimed.
