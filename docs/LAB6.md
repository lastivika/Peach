> Current deployed-model target: Amazon Nova Pro (`amazon.nova-pro-v1:0`). The

> Lab 7 update: Cognito, reports and parser infrastructure is now managed by
> [HCP Terraform](LAB7.md). CloudFormation commands below are historical;
> use `make infra-plan` for those resources.
> user approved this substitution because AWS denied Opus 5.5 access. See ADR 0006.
> Nova uses Converse and the selected-Region model ARN; no Anthropic activation
> step is needed for Nova. Configure matching token rates whenever changing models.

# Lab 6 — Paste, check, save

## Run and deploy

1. Confirm the selected Region in AWS Settings → View all projects → Overview →
   Additional Info → Region (this checkout's AWS profile is `us-east-1`).
2. Set `PARSER_MODEL` (default `amazon.nova-pro-v1:0`) and matching token prices.
   `make llm-hello` prints the actual answer, stop reason and usage. Anthropic
   use-case activation is needed only when selecting an Anthropic model.
3. `make parse TEXT="Planning Monday at 10:00. Discuss pricing with Olena."`
   uses today's date in Europe/Kyiv; `python -m app.ai.cli parse --tz ...` overrides it.
4. Run `uv sync` in backend, tests and migrations. Set BUDGET_EMAIL in local `.env`.
5. For a committed release, use the default immutable commit-SHA images.
   For an authorised uncommitted release, prefix both deploy targets with
   `LOCAL_RELEASE=1`; this freezes non-ignored backend files into a temporary
   content-hashed snapshot and does not create a Git commit.
6. `make deploy-backend` runs migration 0005 before rolling out the API.
7. `make deploy-ai` builds the same backend's `lambda` target and deploys
   `infra/ai.yml`. It writes NEXT_PUBLIC_AGENDA_PARSER_URL to local `.env`.
8. `make deploy-frontend`. The parser URL is compiled into the frontend; the script
   also discovers it from the AI stack for CI builds.
9. Open Calendar → Add agenda. Paste → Parse → review/change a suggested field →
   Save agenda. Reopen to verify persistence.

The parser has no VPC connection and no database access. All new resources carry
PROJECT_NAME where the resource type supports tags. The AWS Budget covers total
monthly project spend, not just the AI function. An alert does not cap spending.

## Checks

- Backend: `TEST_DATABASE_URL=postgresql+asyncpg://peach:peach@localhost:5432/peach_test uv run pytest`
- Frontend: `pnpm test`, `pnpm exec tsc --noEmit`, `pnpm lint`
- Infrastructure: `cfn-lint infra/ai.yml` and
  `cfn-guard validate --rules infra/guard/ai.guard --data infra/ai.yml --output-format json`
- Authentication: POST without a valid Cognito ID token returns 401 before Bedrock.
- Real model evidence: follow `submission/lab6/RESULTS.md`; unit mocks are not live evidence.

## Data and feedback

Migration 0005 adds nullable JSONB columns `agenda` and `ai_suggestion` to existing
meetings. Existing meetings remain compatible. Saving an agenda changes only these
columns, not the meeting's calendar dates/title; parsed schedule fields are agenda
metadata visible for review. The original model output remains unchanged when a
user edits the reviewed form.

No agenda or AI result is saved by parsing. Existing agenda data is preserved if
parsing fails or is cancelled. A browser abort does not guarantee that upstream
inference stops billing. The 30-second Lambda timeout and explicit token budget
bound each invocation. The project-wide quota is ten concurrent executions; AWS does not permit a
two-slot reservation at that quota. Per-user durable rate
limiting is a production follow-up, not implemented as an unreliable in-memory counter.

## Cleanup

To keep the demo available, keep the AI stack. To stop AI charges, delete the
`${PROJECT_NAME}-ai` stack and remove the parser URL from the next frontend build;
the main app and saved agendas remain. The log group is retained by policy; ECR
images are outside the stack and must be cleaned up separately if no longer needed.
Do not drop the agenda columns to disable the optional parser.
