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

On 2026-10-15, one manual SQS request created the `2026-W41` CSV and invoked delivery. One controlled scheduled request created the `2026-W42` CSV and invoked delivery. Both files were 288 bytes. The queue drained after each run. SES aggregate statistics showed two delivery attempts and no bounces/rejects/complaints in the corresponding 15-minute interval. Inbox delivery was not independently verified.

An isolated test queue and Lambda produced three `AccessDenied` failures because the test role intentionally lacked `s3:ListBucket`; its message reached its own DLQ. SQS redrive completed and moved the message once. The post-redrive invocation evidence and cleanup still need verification because the AWS MCP session expired.

Local verification passed: 14 weekly-report handler tests, 2 isolated unit tests, compileall, Ruff, and `git diff --check`. DB-backed tests could not run because local PostgreSQL was unavailable. The production Lambda image has not been rebuilt with the new trigger markers.

## Error handling and duplicate behavior

The worker queue retries failed requests and sends messages to a DLQ after the configured receive count. The local worker code skips an existing report and conditionally writes new objects, preventing a repeated SQS request from replacing the report. Delivery has no deduplication store: replaying the same S3 event can send another email. A production duplicate-week experiment remains outstanding.

## Current limitations

- Deployed Lambdas remain on `sha256:91bcd93248a729df6eba596506bb5cf7927aac76d96cd38aa3f7195e55312c53`; local trigger logging changes are not deployed.
- Production marker evidence `trigger=sqs`, `trigger=schedule`, and `trigger=s3` is therefore not available.
- The isolated test Lambda, execution role, queues, event source mapping, and log group remain to be cleaned up.
- SES is still in sandbox. Aggregate send statistics do not prove inbox delivery.
- Source changes and the submission package were committed and pushed to `main`; the latest prior commit is [11be209](https://github.com/lastivika/Peach/commit/11be2093da7f461ed2072b3d7e4be4f13011efe4). The unrelated `frontend/.prettierignore` change remains uncommitted.

On 2026-10-15, the requested continuation could not access AWS: `aws sts get-caller-identity --profile peach-lab` failed because the sign-in token endpoint was unreachable, AWS MCP returned `Unknown tool`, and `aws login` remained on the sign-in page's loading spinner. No AWS changes, Lambda invocations, ECR login/build/push, or test-resource cleanup were performed in that continuation. The isolated test resources listed below must be treated as still present until verified otherwise.

## Temporary resources requiring cleanup

- Lambda: `peach-step7-worker-test-20261015`
- Event source mapping UUID: `96421c8c-a49c-4e8b-a9ff-845e2ee37469`
- SQS source: `peach-step7-worker-test-20261015-source`
- SQS DLQ: `peach-step7-worker-test-20261015-dlq`
- IAM role: `peach-step7-worker-test-20261015` (inline policy `temporary-test-runtime`)
- CloudWatch log group: `/aws/lambda/peach-step7-worker-test-20261015`

## Conclusion

The deployed worker → S3 → EventBridge → delivery path and one scheduled run were observed successfully. The lab is partially ready for submission: inbox receipt, trigger-marker logs, post-redrive recovery logs, test-resource cleanup, duplicate production behavior, new image deployment, and final GitHub push remain unverified or incomplete.
