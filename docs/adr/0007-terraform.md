# ADR 0007: Adopt Terraform with HCP Terraform runs

Status: Accepted. Migration completed on 2026-10-30 (Europe/Kyiv): 49 imports,
zero recreated resources; verified post-migration no-change plan.

## Context

Peach has existing Cognito users, private report objects, and an authenticated
Bedrock agenda parser. Their current CloudFormation stacks must transfer
ownership without replacing resources. Earlier network, database, ECS and site
stacks remain in CloudFormation. Application delivery already uses GitHub Actions.

## Decision

Use one Terraform root in `infra/` and one HCP Terraform development workspace.
Preserve all deployed names and import existing resources. Add Retain policies
before releasing CloudFormation ownership. Reject migration plans containing
creates, resource value changes or deletes. The approved import exception
allows five sensitivity-only updates with identical before/after values;
this preserves secret redaction, unlike ignoring those attributes. Protect the user pool, client and report bucket with
`prevent_destroy`. Do not remove source templates until verified adoption.

Infrastructure changes follow a GitHub pull request, reviewed HCP plan, merge,
and HCP apply. Workspace permissions determine who can approve runs; AWS uses
short-lived OIDC credentials with trust restricted to this organization and
workspace. The Makefile provides planning and outputs, never an apply command.
GitHub Actions continues deploying application code. When a release needs new
infrastructure, apply the compatible infrastructure first, then deploy the app.
For a destructive contract change use expand, migrate, contract across releases.

## Alternatives

CloudFormation avoids operating a separate state backend but limits our existing
cross-provider and future environment workflow. CDK adds an imperative language
and synthesis layer while retaining CloudFormation. OpenTofu is an open-source
alternative, but this course requires HCP Terraform's VCS-run evidence and we
choose its native CLI workflow. Modules and separate state/workspaces can be
introduced when a real second environment is needed.

## Consequences

HCP holds encrypted remote state and serializes runs using workspace locking.
Sensitive values are hidden from normal plan text, not removed from state.
The Google OAuth secret is a sensitive workspace variable and appears in Cognito
and Terraform state. The existing database URL is read from Secrets Manager and
also appears in the worker's Lambda configuration and Terraform state. State
read access, workspace administration, local private snapshots, and any downloaded
plan/state files therefore require the same care as credentials. No secrets,
state, plans or `submission/` artifacts belong in Git.

HCP downtime blocks routine infrastructure changes; the existing AWS application
continues operating. Wait for recovery when possible. Emergency backend recovery
requires an approved, exclusive maintenance window, a secured latest state
backup, verified lineage/serial, and locking before another backend is used.
Never initialize an empty replacement state or run competing applies. Record any
emergency console change in code before the next plan so it is not reverted.
Terraform can fail midway without automatic rollback: inspect actual resources
and the latest state, correct the cause, and re-plan; do not blindly destroy.

Migration counts, recreated-resource explanations (if any), the no-change plan,
VCS apply and drift evidence must be recorded from actual runs in the local
`submission/lab7/` folder before claiming completion.
