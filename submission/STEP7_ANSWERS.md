# Step 7 — Weekly Meetings Report Results

Evidence below reflects the controlled runs on 2026-10-15 in `us-east-1`. “Observed” means confirmed by the AWS API/CloudWatch/S3/SES statistics. SES aggregate statistics do not prove delivery to an inbox.

## A. Manual report

**Observed:** A single `2026-W41` message (`source=manual`) was sent to the report SQS queue. The queue returned to 0 visible and 0 in-flight messages. The worker had a successful CloudWatch invocation at 2026-10-15 08:47:31–08:47:32 UTC. It created `reports/2026-W41/weekly-meetings.csv` (288 bytes, last modified 08:47:33 UTC). The delivery Lambda had a successful invocation at 08:47:34–08:47:37 UTC. The S3 EventBridge rule had one target pointing to the delivery Lambda and was configured for Object Created keys under `reports/`.

**SES:** The SES `GetSendStatistics` datapoint for the 15-minute interval beginning 08:37 UTC reported 2 delivery attempts and 0 bounces/rejects/complaints. This is consistent with one manual and one scheduled report. It is aggregate evidence, not per-message or inbox confirmation.

**Log marker:** After deploying the corrected image, a duplicate `2026-W41` SQS request logged `trigger=sqs origin=manual outcome=received` and `outcome=already_exists`. The object remained unchanged. The temporary scheduled request logged `trigger=sqs origin=schedule` and `trigger=schedule outcome=queued`, then skipped the same existing object. Both trigger markers are verified in CloudWatch.

## B. Scheduled report

**Observed:** The existing schedule was temporarily set to `rate(5 minutes)`, enabled, and given `{"week":"2026-W42","source":"schedule"}`. The queue mapping was enabled for the test window. A worker invocation completed at 08:48:58–08:48:59 UTC and created `reports/2026-W42/weekly-meetings.csv` (288 bytes, last modified 08:49:00 UTC). The delivery Lambda completed at 08:49:00 UTC. The SQS queue returned to 0 visible / 0 in-flight messages.

**Restoration:** The schedule was returned to `cron(0 7 ? * MON *)`, `Europe/Kyiv`, `DISABLED`, target input `{}`. The production event source mapping returned to `Disabled`. Both states were verified after the run.

**Log marker:** A temporary `rate(1 minute)` run on the existing schedule sent one Scheduler-origin message for `2026-W41`; CloudWatch logged `trigger=schedule outcome=queued` and the existing-object skip. The schedule was restored to its original disabled weekly cron and the SQS mapping was returned to Disabled.

## C. Failure, retries, DLQ, and redrive

An isolated temporary test queue and DLQ were used; the existing production DLQ was not read or modified. A temporary ARM64 test Lambda used the currently deployed worker image and a narrowly scoped test role that initially lacked `s3:ListBucket`. One valid `2026-W41` message failed at the existing-object check with `AccessDenied` three times. The source queue was configured with `maxReceiveCount=3` and 30-second visibility; after the third failure its isolated DLQ showed 1 visible message.

The test role then received `s3:ListBucket` for only the report bucket and exact `2026-W41` prefix. SQS `StartMessageMoveTask` returned `COMPLETED`, moving 1 message back to the isolated source queue. CloudWatch shows a subsequent test Lambda START/END/REPORT with no error; source and DLQ metadata both showed 0 visible/in-flight messages. The isolated mapping, Lambda, queues, role/policy, and log group were then deleted. The production Report DLQ was not read or modified.

The production Report DLQ showed 2 visible / 0 in-flight messages before the isolated experiment. No operation targeted that DLQ.

## D. Duplicate report

**Automated evidence:** Local handler tests pass for worker idempotency (existing-key skip and conditional `IfNoneMatch="*"`) and for delivery behavior. The delivery test `test_repeated_s3_event_can_send_duplicate_email` confirms that replaying an S3 event can send another email because delivery has no deduplication store.

**Production evidence:** One duplicate `2026-W41` SQS message was processed after the logger fix and logged `outcome=already_exists`; the object's size, ETag, and LastModified remained unchanged, and no delivery invocation followed. A Scheduler-origin message for the same existing key also skipped. This confirms SQS-side idempotency. A repeated EventBridge delivery for an existing key can still send another email because delivery has no deduplication store.

**S3 marker:** The deployed delivery Lambda received one EventBridge-shaped test event for an absent `2026-W44` key and logged `trigger=s3 outcome=received`, then `trigger=s3 outcome=failed` on S3 `GetObject` (`AccessDenied` for the missing key). This was deliberately chosen to avoid resending a report email. It verifies event parsing/logging, not successful SES delivery on the new image. Earlier W41/W42 delivery invocations succeeded on the previous image; SES aggregate statistics showed two attempts but do not prove inbox receipt.

## Remaining completion items

1. Capture the genuine AWS Console screenshots listed in `SCREENSHOTS_GUIDE.md`.
2. If the instructor requires a successful `accepted_by_ses` marker from the new image, authorize one additional delivery test knowing it can send a duplicate email; inbox receipt must still be verified in Gmail.
