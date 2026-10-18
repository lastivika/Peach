# ADR 0006: Parse agenda suggestions outside the VPC

Status: accepted; Nova Pro substitution approved by the user.
Date: 2026-10-16

## Context

Peach users receive agendas in Ukrainian or English emails and chat messages. A model
can structure those notes, but its output is untrusted and may invent values. The
existing owner-scoped meetings API and Aurora database remain the source of truth.
The lab requires a separate parser, no NAT, auditable cost, and human review.

## Decision

Use configurable `PARSER_MODEL=amazon.nova-pro-v1:0` through Bedrock Converse
in us-east-1 (see the disclosed model replacement below). Use temperature zero,
4096 maximum output tokens and exactly one `record_agenda` tool. Do not force tool
choice. Validate with Pydantic; send validation errors back at most once. Reject
truncation, refusal, unexpected/multiple tools, and empty non-agenda output.

Run the parser in a separate 512 MB, 30-second Lambda **outside the VPC**. It has
no database credentials or database/network permissions. Its IAM role permits only
`bedrock:InvokeModel` for the selected model ARN in the selected Region and writes
to its own log group. The function URL uses `AuthType: NONE` because Cognito ID-token
verification is performed in the handler before any model call. Signature, issuer,
audience, expiry and token use are validated. CORS permits the deployed site and
POST only; CORS is not authentication. Limit text to 10,000 characters. The project has a ten-execution Lambda quota;
AWS rejected a two-slot reservation because ten slots must remain unreserved.
The parser therefore shares the project quota; it has no per-user rate limiter. A $5 monthly AWS Budget alerts the owner; it is not a spending stop.

The browser passes its local date and IANA time zone, shows progress and supports
AbortController cancellation. Cancellation discards a late response; it cannot stop
a model invocation already executing in Lambda. Every populated suggested field is
marked until edited. Missing values remain empty. Manual entry works when AI is down.

Persist only when the person presses **Save agenda**, using
`PUT /api/v1/meetings/{id}/agenda` on the existing main API. The API applies the same
owner check as meeting CRUD and validates both final agenda and original
`ai_suggestion` (agenda, model, prompt version). Both JSONB values are saved in the
same transaction. Suggestion metadata is client-submitted feedback, not a signed
forensic record. Peach currently isolates individual users, not organisations;
organisation membership is not invented for this lab.

## Alternatives considered

- **Bedrock from the API through a VPC interface endpoint:** keeps private routing
  but adds an always-on endpoint charge and couples optional AI latency to the main
  application. The parser does not need private data access.
- **Direct Anthropic API:** would require a separate API secret and billing path;
  Bedrock uses the Lambda role and the existing AWS billing controls.
- **Regular expressions:** cheap and deterministic for fixed input, but unsuitable
  for multilingual free text, implied structure and relative dates. Still useful
  for deterministic validation, not the primary parser.
- **RAG, vector store, chat and document parsers:** optional stretch goals, not part
  of the required Part 4. No additional data stores are provisioned.

## Consequences

The parser logs one structured JSON event per attempted parse with user subject,
model, prompt version, accumulated tokens, latency, outcome and estimated USD cost.
No token, pasted text or agenda content is logged. Logs retain 14 days.

Rates are configuration: Nova Pro standard inference in us-east-1 is $0.80/$3.20
per million input/output tokens, verified using the AWS Price List API on
2026-10-17. Cost = `(input_tokens * input_rate + output_tokens * output_rate) / 1,000,000`.
These are estimates, not a billing receipt. Actual metering belongs in the local
submission evidence. The earlier Opus rate card is historical evidence only.

Prompt boundaries reduce injection risk but do not prove immunity. An injected
owner can still appear as a suggestion. The model has no write tool, cannot read
other users' data, cannot execute code, and its content is rendered as text. Human
review plus owner-scoped persistence limits the impact.

If Bedrock is unavailable, the parser returns a clear error; manual agendas and
all other Peach features continue working. Re-evaluate saved suggestion/correction
pairs with a frozen held-out dataset before shipping `agenda-v2`.

References: [Lab 6](https://learn.ucu.edu.ua/mod/assign/view.php?id=154722),
[AWS Messages API](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-messages-api.html),
[Bedrock pricing](https://aws.amazon.com/bedrock/pricing/).

## Model replacement — 2026-10-17

The user approved completing the lab with another model after Opus 5.5 continued
to return project-level HTTP 403 despite an active agreement and allowed IAM
permissions. The selected replacement is `amazon.nova-pro-v1:0` through Bedrock
Converse in us-east-1, verified with a real response and structured tool output.
This is a disclosed deviation from the assignment's specified Claude model.

A small adapter translates the existing message/tool contract to Converse and
normalizes the response. Pydantic validation, one validation retry, suggestion
review, Cognito and database persistence remain unchanged. No cross-Region profile
is used. Lambda now permits only `bedrock:InvokeModel` for the selected model ARN;
the previous Mantle wildcard permission is removed. The CLI retains an optional
Claude code path for future access, but production is configured for Nova.

The AWS Price List API on 2026-10-17 gives standard us-east-1 Nova Pro prices of
$0.0008 per 1,000 input tokens and $0.0032 per 1,000 output tokens, equivalent to
$0.80/$3.20 per million. No cache, batch, priority or provisioned rates are used.
