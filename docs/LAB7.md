# Lab 7: Terraform migration

The source stacks are `peach-cognito` (`infra/cognito.yaml`),
`peach-weekly-meetings-report` (`infra/weekly-meetings-report.yaml`), and
`peach-ai` (`infra/ai.yml`). The course's `auth.yml`/`reports.yml` names differ.
Other CloudFormation stacks remain outside this migration.

## Workspace

Use Terraform >=1.10 and the committed provider lock file. Configure an HCP
workspace with Remote execution, GitHub repository `lastivika/Peach`, working
directory `infra`, and the reviewed deployment branch. The cloud block selects `peach-lab7/peach-dev`. Run `terraform login` and
`make infra-init`. HCP variables contain all existing names in `variables.tf`;
non-secret deployment values can be committed to `terraform.tfvars` after
inventory. Never invent replacement names for CloudFormation-generated names.

Set HCP environment variables `TFC_AWS_PROVIDER_AUTH=true` and
`TFC_AWS_RUN_ROLE_ARN` to the bootstrap role. Restrict its trust to
`organization:ORG:project:PROJECT:workspace:WORKSPACE:run_phase:*`, with audience
`aws.workload.identity`. Permissions must cover this workspace's resources only,
including `cognito-idp:DescribeUserPool`, `lambda:GetFunction`, and
`s3:GetBucketNotification`; mutation permissions are similarly scoped. Do not
use an organization-wide wildcard trust or AdministratorAccess.

## Migration sequence

1. Run `python3 scripts/lab7-inventory.py` with valid AWS credentials. Original
   stack templates, parameters and IDs stay in `submission/lab7/private/` (0600).
2. Capture a Cognito user-count and report-object inventory without exporting
   user profiles or object contents. Capture Lambda names, image digests,
   permission statement IDs and existing IAM role names. Inspect live report
   schedule/event-source enabled states; preserve them exactly.
3. Prepare retention-only stack updates: every resource gets both
   `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain`. Review change sets,
   deploy, and verify the deployed templates before deleting stack records.
   Check output consumers first. Never delete a stack with an unretained resource.
4. Populate import blocks with real IDs for every Terraform resource, including
   split S3 settings, IAM inline policies and EventBridge targets. Record the
   CloudFormation-to-Terraform mapping. Plan repeatedly until every managed
   resource value is unchanged. `scripts/check-migration-plan.py` rejects
   adds, updates and deletes by default. The explicitly approved
   `--allow-sensitivity-only --expected-imports 49` exception accepts updates
   only when all before/after values are identical, no values are unknown,
   and only sensitivity metadata differs. The protected remote plan contains
   49 imports and five such metadata updates; no resource values change. Plans/JSON contain secrets: keep
   them private, never commit them or include them in a submission screenshot.
5. Release CloudFormation ownership only after the complete reviewed import plan
   and recoverable snapshots exist. Run the import apply in HCP; verify user and
   object inventories. Save the subsequent no-change plan. Only then delete
   source templates, import blocks and generated scratch configuration.
6. Merge a small tag change through the VCS workspace, capture the
   successful HCP apply URL/screenshot, then change the parser timeout manually,
   run a plan-only drift check and restore via HCP. Record real evidence.

Application code remains on GitHub Actions. Infrastructure dependencies land
first. The report test must not send mail or enable schedules merely to prove
this migration; existing enabled states are preserved.

## Discussion notes

- Import count comes from the actual plan, not the example count of 14. Split
  provider resources mean it differs from the CloudFormation resource count.
- Changing a report bucket name replaces it; changing pool username attributes
  can replace the pool. `prevent_destroy` blocks these plans while configured.
- Remote locking prevents simultaneous state writes. A state file in Git leaks
  secrets and cannot coordinate concurrent applies.
- Losing state loses the resource-to-address mapping, not the AWS resources.
  Recover a secured state version or carefully re-import resources.
- A manually created resource can be imported, deliberately left unmanaged, or
  retired after dependency/data review. Import a required live Peach resource.
- `-target` may unblock a specific failed dependency; `state rm` can transfer
  ownership without deleting infrastructure. Both require a subsequent full plan.
- Staging should be a reviewed module/configuration proposal, separate variables
  and workspace/state, with a human-reviewed plan and pipeline-controlled apply.
- A partner environment reuses modules but has separate provider credentials,
  variables, domain and state. No cross-Region resources are part of this project.

Frontend CI consumes the four non-secret output values through repository
variables `COGNITO_USER_POOL_ID`, `COGNITO_CLIENT_ID`, `COGNITO_DOMAIN`, and
`NEXT_PUBLIC_AGENDA_PARSER_URL`. Refresh those from `terraform output -raw`
after migration; CI does not need access to secret-bearing Terraform state.
Local frontend deployment can read outputs directly when these variables are
not set. Legacy deployment scripts are retired only after adoption completes.

## Verified migration

Completed 2026-10-30 (Europe/Kyiv): 34 CloudFormation resources map to
49 managed Terraform resources (split S3 settings, IAM policies and targets).
No resources were recreated. All 34 source resources received both Retain
policies and reported DELETE_SKIPPED when the three stacks were released.
The protected plan had 49 imports and five sensitivity-only updates; every
before/after value was identical. All other differences were reconciled to AWS.

- Import: https://app.terraform.io/app/peach-lab7/peach-dev/runs/run-sv9UXyi4E7WxY2kM
- Immediate no-change plan: https://app.terraform.io/app/peach-lab7/peach-dev/runs/run-AmiFeJVf1Re3Qccp
- Three Cognito usernames and three S3 object keys/ETags/sizes preserved.
- Lambda ARNs, image digests, environments and timeouts preserved.
- Report schedule remains DISABLED; event-source mapping remains Disabled.
- Frontend/health HTTP 200; unauthenticated API HTTP 401.

The bootstrap OIDC provider and `peach-terraform-dev` role remain outside this
root, so the workspace cannot modify its own trust. Its subject is restricted
to `organization:peach-lab7:project:Default Project:workspace:peach-dev:run_phase:*`.
AWS permissions were generated with IAM Policy Autopilot, reviewed and scoped
to existing resources; no AdministratorAccess. The workspace has six variables:
two OIDC environment variables and four sensitive Terraform inputs.
