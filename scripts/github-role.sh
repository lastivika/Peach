#!/usr/bin/env bash
# .env is local configuration; backticks inside JMESPath queries are literals.
# shellcheck disable=SC1091,SC2016
# Create the IAM role GitHub Actions assumes to deploy, and point the
# repository at it. No access key is created or stored anywhere.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="${ROOT}/infra/github-oidc.yaml"

log() { printf '\033[36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[33m==>\033[0m %s\n' "$*" >&2; }
die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

if [[ -f "${ROOT}/.env" ]]; then
  # Variables already exported win over .env: `AWS_REGION=eu-central-1 make x`
  # must not be quietly reset to the region .env names.
  preset="$(export -p)"
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
  eval "${preset}"
fi

for var in AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN; do
  [[ -n "${!var:-}" ]] || unset "${var}"
done

PROJECT_NAME="${PROJECT_NAME:-peach}"
STACK_NAME="${GITHUB_ROLE_STACK_NAME:-${PROJECT_NAME}-github-oidc}"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
export AWS_DEFAULT_REGION="${AWS_REGION}"

command -v aws >/dev/null 2>&1 || die "aws cli is required"
aws sts get-caller-identity >/dev/null 2>&1 \
  || die "no usable AWS credentials - set AWS_PROFILE or the AWS_* keys in .env"

# --- which repository ---------------------------------------------------------

REPO="${GITHUB_REPO:?Set GITHUB_REPO explicitly to your own owner/repository}"
[[ "${REPO}" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || die "invalid GITHUB_REPO"
CALLER="$(aws sts get-caller-identity --query Arn --output text)"
[[ "${CALLER}" != *:root ]] || die "Use your non-root IAM administrator for bootstrap"
DISTRIBUTION_ID="$(aws cloudformation describe-stacks --stack-name "${PROJECT_NAME}-frontend" \
  --query "Stacks[0].Outputs[?OutputKey=='DistributionId'].OutputValue" --output text)"
log "trusting only repo:${REPO}:ref:refs/heads/main"

# --- the account may already have a GitHub provider ---------------------------

# IAM allows exactly one provider per issuer URL, so creating a second fails.
EXISTING_PROVIDER="$(aws iam list-open-id-connect-providers \
  --query "OpenIDConnectProviderList[?contains(Arn, 'token.actions.githubusercontent.com')]|[0].Arn" \
  --output text 2>/dev/null || true)"
[[ "${EXISTING_PROVIDER}" == "None" ]] && EXISTING_PROVIDER=""
# Keep a provider owned by this stack under its original logical resource.
OWNED_PROVIDER="$(aws cloudformation describe-stack-resource --stack-name "${STACK_NAME}" \
  --logical-resource-id OidcProvider --query StackResourceDetail.PhysicalResourceId \
  --output text 2>/dev/null || true)"
if [[ -n "${OWNED_PROVIDER}" && "${OWNED_PROVIDER}" == "${EXISTING_PROVIDER}" ]]; then
  EXISTING_PROVIDER=""
fi


if [[ -n "${EXISTING_PROVIDER}" ]]; then
  log "reusing the GitHub OIDC provider already in this account"
else
  log "this account has no GitHub OIDC provider yet - the stack creates one"
fi

# --- deploy -------------------------------------------------------------------

if ! aws cloudformation deploy \
  --stack-name "${STACK_NAME}" \
  --template-file "${TEMPLATE}" \
  --parameter-overrides \
    "ProjectName=${PROJECT_NAME}" \
    "GitHubRepo=${REPO}" \
    "FrontendDistributionId=${DISTRIBUTION_ID}" \
    "ExistingProviderArn=${EXISTING_PROVIDER}" \
  --capabilities CAPABILITY_NAMED_IAM \
  --no-fail-on-empty-changeset \
  --tags "PROJECT_NAME=${PROJECT_NAME}"; then
  warn "deploy failed - most recent failure reasons:"
  aws cloudformation describe-stack-events --stack-name "${STACK_NAME}" \
    --max-items 30 \
    --query 'StackEvents[?ResourceStatus==`CREATE_FAILED`||ResourceStatus==`UPDATE_FAILED`].[LogicalResourceId,ResourceStatusReason]' \
    --output table >&2 || true
  exit 1
fi

ROLE_ARN="$(aws cloudformation describe-stacks --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='RoleArn'].OutputValue" --output text)"

log "role ready: ${ROLE_ARN}"

# --- tell the repository about it ---------------------------------------------

# Not a secret: the ARN is useless without a token from this repo's workflows.
if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  log "setting repository variables with gh"
  gh variable set AWS_DEPLOY_ROLE_ARN --repo "${REPO}" --body "${ROLE_ARN}"
  gh variable set AWS_REGION --repo "${REPO}" --body "${AWS_REGION}"
  echo
  echo "  Done. Every passing push to main deploys the backend and frontend."
else
  echo
  echo "  gh is not installed or not logged in. Set these two repository"
  echo "  variables by hand, under Settings -> Secrets and variables -> Actions:"
  echo
  echo "    AWS_DEPLOY_ROLE_ARN = ${ROLE_ARN}"
  echo "    AWS_REGION          = ${AWS_REGION}"
  echo
fi
