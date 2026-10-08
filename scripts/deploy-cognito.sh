#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE="${ROOT}/infra/cognito.yaml"

if [[ -f "${ROOT}/.env" ]]; then
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

die() { echo "error: $*" >&2; exit 1; }
log() { printf '\033[36m==>\033[0m %s\n' "$*"; }

command -v aws >/dev/null 2>&1 || die "aws CLI is required"

PROJECT_NAME="${PROJECT_NAME:-peach}"
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
export AWS_DEFAULT_REGION="${AWS_REGION}"
STACK_NAME="${COGNITO_STACK_NAME:-${PROJECT_NAME}-cognito}"

aws sts get-caller-identity >/dev/null 2>&1 || die "No usable AWS credentials"
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
CALLER="$(aws sts get-caller-identity --query Arn --output text)"
[[ "${CALLER}" != *:root ]] || die "Use a non-root IAM user or role"

GOOGLE_CLIENT_ID="${GOOGLE_OAUTH_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_OAUTH_CLIENT_SECRET:-}"
[[ -n "${GOOGLE_CLIENT_ID}" ]] || die "Set GOOGLE_OAUTH_CLIENT_ID in .env"
[[ -n "${GOOGLE_CLIENT_SECRET}" ]] || die "Set GOOGLE_OAUTH_CLIENT_SECRET in .env"

# Match the existing Cognito domain by default; override only if you need a
# different globally unique prefix.
DOMAIN_PREFIX="${COGNITO_DOMAIN_PREFIX:-${PROJECT_NAME}-${ACCOUNT_ID}-login}"

if [[ -n "${SITE_URL:-}" ]]; then
  FRONTEND_URL="${SITE_URL%/}"
else
  FRONTEND_URL="$(aws cloudformation describe-stacks \
    --stack-name "${PROJECT_NAME}-frontend" \
    --query "Stacks[0].Outputs[?OutputKey=='SiteUrl'].OutputValue" \
    --output text 2>/dev/null || true)"
  FRONTEND_URL="${FRONTEND_URL%/}"
fi
[[ "${FRONTEND_URL}" == https://* ]] \
  || die "Could not discover an HTTPS frontend URL. Set SITE_URL in .env."

COGNITO_ORIGIN="https://${DOMAIN_PREFIX}.auth.${AWS_REGION}.amazoncognito.com"

echo
log "Google OAuth must contain these exact values:"
echo "  Authorized JavaScript origin: ${COGNITO_ORIGIN}"
echo "  Authorized redirect URI:      ${COGNITO_ORIGIN}/oauth2/idpresponse"
echo

log "deploying ${STACK_NAME} for ${FRONTEND_URL}"
aws cloudformation deploy \
  --stack-name "${STACK_NAME}" \
  --template-file "${TEMPLATE}" \
  --parameter-overrides \
    "ProjectName=${PROJECT_NAME}" \
    "SiteUrl=${FRONTEND_URL}" \
    "DomainPrefix=${DOMAIN_PREFIX}" \
    "GoogleClientId=${GOOGLE_CLIENT_ID}" \
    "GoogleClientSecret=${GOOGLE_CLIENT_SECRET}" \
  --no-fail-on-empty-changeset \
  --tags "PROJECT_NAME=${PROJECT_NAME}"

output() {
  aws cloudformation describe-stacks --stack-name "${STACK_NAME}" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}

USER_POOL_ID="$(output UserPoolId)"
CLIENT_ID="$(output ClientId)"
DOMAIN="$(output Domain)"

python3 - "${ROOT}/.env" "${USER_POOL_ID}" "${CLIENT_ID}" "${DOMAIN}" \
  "${AWS_REGION}" "${DOMAIN_PREFIX}" "${FRONTEND_URL}" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
values = {
    "COGNITO_USER_POOL_ID": sys.argv[2],
    "COGNITO_CLIENT_ID": sys.argv[3],
    "COGNITO_DOMAIN": sys.argv[4],
    "COGNITO_REGION": sys.argv[5],
    "COGNITO_DOMAIN_PREFIX": sys.argv[6],
    "SITE_URL": sys.argv[7],
}
lines = path.read_text().splitlines() if path.exists() else []
keys = tuple(f"{key}=" for key in values)
lines = [line for line in lines if not line.startswith(keys)]
lines.extend(f"{key}={value}" for key, value in values.items())
path.write_text("\n".join(lines) + "\n")
PY

echo
log "Cognito deployed"
echo "  login URL: ${FRONTEND_URL}/login/"
echo "  user pool: ${USER_POOL_ID}"
echo "  client:    ${CLIENT_ID}"
echo "  domain:    https://${DOMAIN}"
echo
echo "Next: make deploy-frontend"
