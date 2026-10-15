# Step 7 — Weekly Meetings Report Results

Evidence below reflects the controlled runs on 2026-10-15 in `us-east-1`. “Observed” means confirmed by the AWS API/CloudWatch/S3/SES statistics. SES aggregate statistics do not prove delivery to an inbox.

## A. Manual report

**Observed:** A single `2026-W41` message (`source=manual`) was sent to the report SQS queue. The queue returned to 0 visible and 0 in-flight messages. The worker had a successful CloudWatch invocation at 2026-10-15 08:47:31–08:47:32 UTC. It created `reports/2026-W41/weekly-meetings.csv` (288 bytes, last modified 08:47:33 UTC). The delivery Lambda had a successful invocation at 08:47:34–08:47:37 UTC. The S3 EventBridge rule had one target pointing to the delivery Lambda and was configured for Object Created keys under `reports/`.

**SES:** The SES `GetSendStatistics` datapoint for the 15-minute interval beginning 08:37 UTC reported 2 delivery attempts and 0 bounces/rejects/complaints. This is consistent with one manual and one scheduled report. It is aggregate evidence, not per-message or inbox confirmation.

**Log marker:** The deployed worker image did not emit `trigger=sqs` / `trigger=schedule`, and the deployed delivery image did not emit `trigger=s3`. Those markers exist in the local source changes but were not deployed because ECR publication was blocked. The invocation and object timestamps corroborate the event path, but the marker requirement is **NOT VERIFIED**.

## B. Scheduled report

**Observed:** The existing schedule was temporarily set to `rate(5 minutes)`, enabled, and given `{"week":"2026-W42","source":"schedule"}`. The queue mapping was enabled for the test window. A worker invocation completed at 08:48:58–08:48:59 UTC and created `reports/2026-W42/weekly-meetings.csv` (288 bytes, last modified 08:49:00 UTC). The delivery Lambda completed at 08:49:00 UTC. The SQS queue returned to 0 visible / 0 in-flight messages.

**Restoration:** The schedule was returned to `cron(0 7 ? * MON *)`, `Europe/Kyiv`, `DISABLED`, target input `{}`. The production event source mapping returned to `Disabled`. Both states were verified after the run.

**Log marker:** The deployed worker did not log `trigger=schedule`; the log marker itself is **NOT VERIFIED**.

## C. Failure, retries, DLQ, and redrive

An isolated temporary test queue and DLQ were used; the existing production DLQ was not read or modified. A temporary ARM64 test Lambda used the currently deployed worker image and a narrowly scoped test role that initially lacked `s3:ListBucket`. One valid `2026-W41` message failed at the existing-object check with `AccessDenied` three times. The source queue was configured with `maxReceiveCount=3` and 30-second visibility; after the third failure its isolated DLQ showed 1 visible message.

The test role then received `s3:ListBucket` for only the report bucket and exact `2026-W41` prefix. SQS `StartMessageMoveTask` returned `COMPLETED`, moving 1 message back to the isolated source queue. Subsequent queue metadata showed 0 visible/in-flight messages in both temporary queues. **The post-redrive Lambda log check and temporary-resource cleanup are not verified** because the AWS MCP session expired immediately afterward. Do not treat recovery or cleanup as complete until those are confirmed.

The production Report DLQ showed 2 visible / 0 in-flight messages before the isolated experiment. No operation targeted that DLQ.

## D. Duplicate report

**Automated evidence:** Local handler tests pass for worker idempotency (existing-key skip and conditional `IfNoneMatch="*"`) and for delivery behavior. The delivery test `test_repeated_s3_event_can_send_duplicate_email` confirms that replaying an S3 event can send another email because delivery has no deduplication store.

**Production evidence:** A second production request for the same week was not sent. Therefore production duplicate counts are **NOT VERIFIED**. Based on the implementation, a repeated SQS request for an existing S3 key skips generation and does not create a second S3 Object Created event. A repeated EventBridge delivery for the same existing key can send a duplicate email.

## Remaining completion items

1. Reconnect AWS MCP, verify the test Lambda logs after redrive, then remove the temporary mapping, Lambda, role, queues, and log group listed in `FINAL_REPORT.md`.
2. Resolve a credential-safe ECR push path, publish the locally tested image, and deploy it through a reviewed CloudFormation change set. The local `trigger=*` logging changes are not in the deployed digest.
3. Run one duplicate-week SQS test after cleanup; verify no new S3 object and no extra SES attempt.
4. Verify mailbox receipt manually if the instructor requires proof of inbox delivery.
