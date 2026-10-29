# Weekly meetings report lab

> Lab 7 update: Cognito, reports and parser infrastructure is now managed by
> [HCP Terraform](LAB7.md). CloudFormation commands below are historical;
> use `make infra-plan` for those resources.

This optional pipeline reuses Peach's existing `meetings` table and PostgreSQL
connection. It does not create another meeting store or add participant
relationships. `Meeting.owner_id` is the available organizer identifier.

## Data and report contract

`build_weekly_report(week=None)` returns UTF-8 CSV bytes. It accepts an ISO week
such as `2026-W39`; omitted weeks use the current ISO week in `Europe/Kyiv`.
Intervals are local Monday midnight inclusive through the following Monday
midnight exclusive, converted to UTC for PostgreSQL queries. A meeting is
included based on `start_at`, and its full duration is counted. The CSV has
overall totals, summaries grouped by organizer UUID, previous-week comparisons,
and the five longest meetings. Peach has no participant model, so there are no
participant metrics.

The report includes organization-wide totals, organizer IDs, meeting titles,
and exact times. Only an explicitly authorized recipient should receive it.
The email attaches the CSV and requests a private presigned S3 link with an
expiry of up to seven days. Lambda signs it with temporary execution-role
credentials, so the link may expire earlier when those credentials expire. The
email communicates that limitation to the recipient. The link is generated
only for the message and is not logged.
The mailer uses SES v2 `SendEmail` with raw MIME content, so its IAM action is
`ses:SendEmail` scoped to the configured sender identity; it does not call the
SES v1 `SendRawEmail` API/action. Verify the sender and, in sandbox, recipient
identities; also confirm production sending access before an authorized test.

## Event flow

1. EventBridge Scheduler is configured for Mondays at 07:00 in `Europe/Kyiv`;
   its default state is `DISABLED`. It sends `{}` directly to the report SQS
   queue. The worker resolves that to the previous completed Kyiv ISO week.
2. The SQS-triggered report Lambda queries the existing PostgreSQL database,
   builds the report, and stores `reports/YYYY-Www/weekly-meetings.csv` in a
   private, encrypted S3 bucket. Objects under `reports/` expire after 90 days.
3. S3 object-created events go to EventBridge. A non-VPC delivery Lambda reads
   the CSV, attaches it to a SES raw MIME email, and includes the private link
   requested with an expiry of up to seven days (subject to credential expiry).

The report Lambda runs in the existing VPC. The stack adds a source-restricted
PostgreSQL ingress rule and, when requested, an S3 gateway endpoint for the
selected route tables. SES and the delivery Lambda stay outside the database VPC;
the report Lambda needs S3 HTTPS through the gateway endpoint and no SES or NAT
path. Every report subnet must belong to `VpcId`, reach the database security
group on TCP/5432, and have a route table included in `PrivateRouteTableIds`. If
an S3 gateway endpoint already serves those route tables, confirm its policy
allows `s3:GetObject` and `s3:PutObject` on this report bucket before setting
`AttachS3GatewayEndpoint=false`; this stack does not modify an existing endpoint
policy. The S3 prefix-list ID and endpoint service must match the selected Region.
The endpoint policy also allows `s3:GetObject` from the selected Region's ECR
`prod-<region>-starport-layer-bucket`, because all subnets using an attached
route table use that endpoint for S3 and ECS/Fargate pulls private ECR image
layers through S3. The endpoint policy does not grant IAM permissions by itself.

In the currently inspected Peach VPC, all six subnets have public-IP-on-launch
enabled and use one main route table with a route to the Internet Gateway; there
are no separate private route tables or existing S3 gateway endpoint. Lambda ENIs
do not receive public IP addresses, so this does not provide the report function
general internet access. The report function only needs the database and S3, but
the endpoint would attach to the shared main route table and affect S3 routing for
all its subnets. Before creating that endpoint, review the endpoint policy and
confirm whether other workloads in those subnets require S3 access beyond ECR
image layers. Do not describe those current subnets as private.
The SQS event source uses batch size one and maximum concurrency two without
reserving account-wide Lambda concurrency. Report writes use S3
`If-None-Match: *`; concurrent duplicate deliveries cannot overwrite an
existing deterministic key, and the losing invocation treats the S3 412 as an
already-created report. SQS report failures use a redrive DLQ. Scheduler
invocation failures and delivery Lambda failures are also routed to their
configured DLQs. S3 events are filtered to `reports/`; the delivery Lambda does
not write to the bucket, so its processing cannot trigger a recursive report
event. EventBridge/S3 delivery is at least once, so duplicate S3 notifications
may cause duplicate emails; exactly-once SES delivery is not guaranteed.

## Local verification

Run the report tests with the existing PostgreSQL-backed backend suite:

```sh
docker compose exec -T backend pytest
docker compose exec -T backend ruff check .
docker compose exec -T backend ruff format --check .
python3 -m unittest discover -s tests -v
```

Report builder tests insert temporary meetings into the test database and cover
ISO-year boundaries, Kyiv-to-UTC conversion, CSV escaping, owner aggregates,
previous-week comparison, and top-five ordering. Handler tests stub AWS SDK
calls; they do not send email or create AWS resources.

Delivery Lambda failures are retried and sent to `DeliveryDlq` after the
configured attempts. The same queue receives EventBridge target-delivery
failures. The template does not create CloudWatch alarms or a DLQ consumer;
operators must inspect the delivery Lambda log group and queue after a failure.
The report worker SQS redrive queue and Scheduler target DLQ are separate.

## Deployment failure note

The first CloudFormation CREATE attempt failed at `WeeklySchedule` because
EventBridge Scheduler could not assume `SchedulerRole`, and the stack rolled
back. The trust policy had scoped `aws:SourceArn` to the individual schedule
ARN. Scheduler requires this condition to use the schedule group ARN; the
template now scopes it to `SchedulerGroup.Arn` while retaining the account
condition and least-privilege SQS send permissions. See [Scheduler confused
deputy prevention](https://docs.aws.amazon.com/scheduler/latest/UserGuide/cross-service-confused-deputy-prevention.html).

A later CREATE attempt created `WeeklySchedule`, then rolled back when CloudFormation
tried to retrieve its `Arn` using `GetSchedule` without `groupName`; CloudTrail
recorded `ResourceNotFoundException` because the schedule belongs to the
non-default `peach-weekly-reports` group. CloudFormation documents `Arn` as a
supported `GetAtt` attribute, and the successful `CreateSchedule` response
contained the expected ARN. The `ScheduleArn` output now constructs that ARN
with `Fn::Sub`, using the partition, Region, account, group name, and schedule
name. This avoids the failing lookup while leaving the schedule resource,
disabled state, and timing unchanged.

## Manual prerequisites

Before preparing a stack change:

1. Confirm the project's selected Region in **AWS Settings → View all projects →
   Overview → Additional Info → Region**. Use that one Region for the stack,
   existing Peach VPC/database, ECR image, S3 prefix-list ID, and SES identity.
   Do not infer the Region from a local `.env` file.
2. Sign in with the approved AWS profile/session (for this AWS experience use
   `aws login --profile "$AWS_PROFILE"` when needed). Do not put credentials in
   repository files. Verify the active identity with
   `aws sts get-caller-identity --profile "$AWS_PROFILE" --region "$AWS_REGION"`.
3. Verify the SES sender identity in the selected Region. In SES sandbox, the
   recipient must also be verified; outside sandbox, confirm SES production
   sending access. Obtain explicit authorization for the recipient to receive
   organization-wide meeting details. The SES v2 API permits up to 40 MB total
   message size including MIME/base64 attachment encoding; keep the report
   below that limit ([SES quotas](https://docs.aws.amazon.com/ses/latest/dg/quotas.html),
   [SES attachment handling](https://docs.aws.amazon.com/ses/latest/dg/attachments.html)).
4. Identify, from existing infrastructure outputs/configuration, the VPC ID,
   database-reachable subnet IDs and route-table IDs (verify whether each is
   actually private or public-routed), database security-group ID,
   Secrets Manager ARN holding the SQLAlchemy asyncpg URL, selected Region's
   AWS-managed S3 prefix-list ID, and the existing Lambda-compatible backend
   ECR repository/image URI. Never paste secret values into deployment
   parameters; the stack references the existing secret ARN dynamically.
5. Check if those route tables already have an S3 gateway endpoint. Set
   `AttachS3GatewayEndpoint=false` only if an existing endpoint already covers
   them; otherwise the stack creates one and adds S3 routes to each selected
   route table. Review the route-table blast radius first, especially when a
   selected table is shared with ECS/Fargate. The created endpoint policy allows
   the report bucket objects and the selected Region's ECR image-layer bucket.
   Ensure the database security group permits the narrowly scoped ingress rule
   from the report Lambda.
6. Build/push the Lambda-compatible image only to an already-existing ECR
   repository after code review and separate authorization for that AWS write.
   The backend Dockerfile's `lambda` target and CloudFormation functions both
   use `arm64`. The normal `make deploy-backend` path publishes the Dockerfile's
   `runtime` target to the ECS repository; that image is not Lambda-compatible.
   `scripts/deploy-lambda.sh` uses the `lambda` target but also deploys the
   separate legacy stack, so do not run it as an image-only shortcut. Build the
   `lambda` target explicitly below and verify the resulting image URI/digest.

The local `AWS-LAB.md` documents the current Aurora and ECS/Fargate deployment.
Reuse its existing database; do not create a second one. The parameters that
must be confirmed are `ImageUri`, `VpcId`, `PrivateSubnetIds`,
`PrivateRouteTableIds`, `S3PrefixListId`, `AttachS3GatewayEndpoint`,
`DatabaseSecurityGroupId`, `DatabaseUrlSecretArn`, `ReportSenderEmail`, and
`ReportRecipientEmail`. Use `ScheduleState=DISABLED` for initial provisioning.

`DatabaseUrlSecretArn` is supplied as an ARN and used in a Secrets Manager
dynamic reference for the Lambda `DATABASE_URL`. CloudFormation resolves the
secret during resource create/update; the DB URL is therefore present in the
Lambda environment configuration. The report Lambda role does not call
Secrets Manager and has no `secretsmanager:GetSecretValue` grant. The identity
creating/updating the stack (or its CloudFormation execution role) must have
`secretsmanager:GetSecretValue` on this specific secret. Secret rotation alone
does not refresh the Lambda environment; a resource update is needed. Confirm
that the existing secret's `SecretString` is the full SQLAlchemy asyncpg URL,
without printing or copying it into command output. See [CloudFormation dynamic
references](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/dynamic-references-secretsmanager.html).

After separate approval to publish the Lambda image, set the confirmed account,
existing repository, and immutable tag, then build/push from the repository
root. This writes an image to ECR:

```sh
export REPORT_IMAGE_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPORT_ECR_REPOSITORY}:${IMAGE_TAG}"
aws ecr get-login-password --region "$AWS_REGION" --profile "$AWS_PROFILE" \
  | docker login --username AWS --password-stdin "${REPORT_IMAGE_URI%%/*}"
docker buildx build --platform linux/arm64 --target lambda \
  --provenance=false --sbom=false --tag "$REPORT_IMAGE_URI" --push backend
```

## Read-only template validation

These local checks do not access AWS:

```sh
python3 - <<'PY'
import yaml

class CloudFormationLoader(yaml.SafeLoader):
    pass

def intrinsic(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node)
    else:
        value = loader.construct_mapping(node)
    return {"!" + suffix: value}

CloudFormationLoader.add_multi_constructor("!", intrinsic)

with open("infra/weekly-meetings-report.yaml", encoding="utf-8") as template:
    parsed = yaml.load(template, Loader=CloudFormationLoader)
assert parsed["Resources"]["WeeklySchedule"]["Properties"]["State"] == {"!Ref": "ScheduleState"}
assert parsed["Parameters"]["ScheduleState"]["Default"] == "DISABLED"
print("CloudFormation YAML parsed; Scheduler default is DISABLED")
PY
```

The repository CI pins `cfn-lint==1.57.1`. If it is absent locally, use an
isolated temporary virtual environment instead of a global install:

```sh
python3 -m venv /tmp/peach-cfn-lint
/tmp/peach-cfn-lint/bin/python -m pip install cfn-lint==1.57.1
/tmp/peach-cfn-lint/bin/cfn-lint infra/weekly-meetings-report.yaml
```

After a valid AWS profile and parameters are available, CloudFormation's
service-side template validation is read-only:

```sh
aws cloudformation validate-template \
  --template-body file://infra/weekly-meetings-report.yaml \
  --region "$AWS_REGION" --profile "$AWS_PROFILE"
```

## Change set preparation

Creating a change set writes an AWS resource. It requires explicit user
authorization; do not infer authorization from this document. Before requesting
that authorization, confirm all parameter values and review the route-table
impact. The following is an example only and is not authorized by the current
read-only audit. If separately authorized, use confirmed values and keep the
schedule disabled. Review every proposed change before execution; stop if
unrelated resources would be replaced/deleted or if the shared VPC route-table
effects are not acceptable:

```sh
CHANGE_SET_NAME="weekly-report-review-$(date +%Y%m%d%H%M%S)"

aws cloudformation create-change-set \
  --stack-name peach-weekly-meetings-report \
  --change-set-name "$CHANGE_SET_NAME" \
  --change-set-type CREATE \
  --template-body file://infra/weekly-meetings-report.yaml \
  --capabilities CAPABILITY_IAM \
  --region "$AWS_REGION" --profile "$AWS_PROFILE" \
  --parameters \
    ParameterKey=ImageUri,ParameterValue="$REPORT_IMAGE_URI" \
    ParameterKey=VpcId,ParameterValue="$AWS_VPC_ID" \
    ParameterKey=PrivateSubnetIds,ParameterValue="$AWS_PRIVATE_SUBNET_IDS" \
    ParameterKey=PrivateRouteTableIds,ParameterValue="$AWS_PRIVATE_ROUTE_TABLE_IDS" \
    ParameterKey=S3PrefixListId,ParameterValue="$AWS_S3_PREFIX_LIST_ID" \
    ParameterKey=AttachS3GatewayEndpoint,ParameterValue="$ATTACH_S3_GATEWAY_ENDPOINT" \
    ParameterKey=DatabaseSecurityGroupId,ParameterValue="$DATABASE_SECURITY_GROUP_ID" \
    ParameterKey=DatabaseUrlSecretArn,ParameterValue="$DATABASE_URL_SECRET_ARN" \
    ParameterKey=ReportSenderEmail,ParameterValue="$REPORT_SENDER_EMAIL" \
    ParameterKey=ReportRecipientEmail,ParameterValue="$REPORT_RECIPIENT_EMAIL" \
    ParameterKey=ScheduleState,ParameterValue=DISABLED

aws cloudformation describe-change-set \
  --stack-name peach-weekly-meetings-report \
  --change-set-name "$CHANGE_SET_NAME" \
  --region "$AWS_REGION" --profile "$AWS_PROFILE"
```

For an existing report stack, use `--change-set-type UPDATE` after checking the
stack's current status; do not assume the stack exists. Keep `ProjectName`
stable on updates because it determines fixed Lambda and ScheduleGroup names.
The report bucket uses `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain`;
deleting the stack can therefore leave its bucket and reports behind. Inspect
every bucket change in the change set. Do not run `execute-change-set` until
all required parameters are confirmed and the change set is reviewed as safe.
After an approved initial stack creation, verify resources and logs, run a
manually authorized test message/report and confirm SES delivery before
considering any later update to `ScheduleState=ENABLED`. The default remains
disabled. No AWS resource, email, or S3 object is created by this repository
audit.

## Verification record (2026-10-14)

The following are observed results, not deployment claims:

- Local verification passed: backend tests in Docker Compose (`37 passed`),
  deployment contract tests (`6 passed`), frontend tests (`18 passed`), Ruff
  check and format check, frontend ESLint, Prettier, TypeScript `tsc --noEmit`,
  CloudFormation YAML parsing, `cfn-lint`, and `git diff --check`. The Lambda
  target also built locally as `linux/arm64`; `boto3`, `asyncpg`, and both
  report handlers imported successfully in that image. No image was published
  during this verification.
- AWS identity and read-only describe calls succeeded for the Peach lab
  principal in `us-east-1`. The report stack is `ROLLBACK_COMPLETE` and has a
  deletion timestamp. Its stack resources are `DELETE_COMPLETE` except the
  report bucket, which was retained by `DeletionPolicy: Retain`.
- The retained bucket is
  `peach-weekly-meetings-report-reportbucket-gkxkzxoqoe3d`. Its recursive S3
  listing was empty. Public access blocking, AES256 default encryption, and a
  90-day lifecycle rule filtered to `reports/` were confirmed. The S3 gateway
  endpoint `vpce-0a86076b61959252d` is `DELETE_COMPLETE`; no S3 gateway endpoint
  currently exists for the Peach VPC.
- The failed CREATE was caused by `ReservedConcurrentExecutions` leaving fewer
  than ten unreserved Lambda concurrency slots. The current template no longer
  reserves account-wide concurrency and caps the SQS event source at two.
  Worker/delivery Lambdas, queues/DLQs, their log groups, database ingress, and
  Scheduler resources were removed during rollback. No report CloudWatch log
  groups or report SQS queues currently exist, and the Scheduler group is
  absent. The template still defaults `ScheduleState` to `DISABLED`.
- The existing Aurora cluster `peach-db` was `available`; the configured
  Secrets Manager ARN was confirmed by metadata only. The report subnet list
  uses five existing subnets; all six VPC subnets have public-IP-on-launch
  enabled and share main route table `rtb-0ad83fa6105fe5427`, whose default
  route targets an Internet Gateway. This is not a private subnet topology.
  The regional S3 prefix-list ID `pl-63a5400a` was confirmed.
- The existing ECR tag `weekly-report-20261013-01` was present. It predates the
  latest local worker/template corrections; the current image still needs a
  separately authorized ECR push before it can be used for a deployment.
- SES is still in sandbox (`ProductionAccessEnabled: false`) and the configured
  sender identity reports `VerifiedForSendingStatus: false`. No report email
  was verified as delivered. Do not run the intentional email test until the
  identity status is true and deployment validation is complete. A fresh SES
  identity verification message was requested with the user's prior
  authorization; AWS still reported `false` immediately afterward, so its link
  must be clicked before retrying the status check.

These AWS observations do not verify any successful report trigger, database
query by Lambda, S3 object creation by Lambda, SQS redrive, Scheduler invocation,
or SES report delivery. All require the stack to be successfully deployed and
the manual end-to-end run to complete. The assignment file named
`Pasted markdown(3).md` was not present in the repository during this check; add
it or provide its exact theoretical questions before marking those answers
complete.

## Deployment readiness

**Local PASS:** the previously run backend suite passed 37 tests, frontend
passed 18, and the original deploy contract passed 6. In this follow-up, the
report handler tests passed 7 and the deploy contract plus report infrastructure
contract passed 9. Ruff check/format passed for the changed Python test files;
documentation Prettier and `git diff --check` passed. CloudFormation lint and
service validation passed in the preceding verification. The ARM64 Lambda image
build and handler imports passed locally; no current image was published.

**AWS unverified:** the last read-only inspection found the stack rolled back,
the report queues/functions/log groups and Scheduler group absent, and only the
empty retained S3 bucket remaining. No builder query, S3 report object, S3 event,
CloudWatch trigger log, SQS DLQ movement/redrive, or report email has been
verified. SES was still sandboxed and its identity status was false at the last
check. The Builder subnets are public-routed; Lambda ENIs have no public IP. The
current no-NAT path is Aurora through the VPC-local route plus S3 through a
Gateway Endpoint. Attaching that endpoint to the sole shared main route table
affects S3 routing for all six subnets; the endpoint policy must retain the
report prefix and regional ECR image-layer bucket permissions.

The assignment file is missing, current code is not published to ECR, and SES
verification is not confirmed. No deployment or change set is authorized by
this record. Safe continuation order: (1) supply the official assignment and
confirm its required final Scheduler state; (2) explicitly authorize publishing
the current ARM64 image to the existing ECR repository; (3) verify the already
requested SES identity returns `VerifiedForSendingStatus=true`; (4) confirm the
current VPC, subnet, route-table, DB secret ARN, and shared-route-table impact;
(5) separately authorize a CREATE change set, review every resource and shared
route effect, then obtain explicit authorization before executing it; (6) keep
Scheduler disabled through deployment and manual validation; (7) use only the
single authorized report email, collect real S3/CloudWatch/SQS/SES evidence, and
verify the actual Scheduler state against the official assignment.
