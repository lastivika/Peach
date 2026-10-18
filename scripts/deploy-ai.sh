#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT}/.env" ]]; then
  preset="$(export -p)"
  set -a
  source "${ROOT}/.env"
  set +a
  eval "${preset}"
fi
for var in AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN; do
  [[ -n "${!var:-}" ]] || unset "${var}"
done
: "${AWS_REGION:?Set the selected AWS Region}"
: "${BUDGET_EMAIL:?Set BUDGET_EMAIL for the monthly five-dollar alert}"
: "${SITE_URL:?Set the deployed site origin}"
export AWS_DEFAULT_REGION="${AWS_REGION}"
PROJECT_NAME="${PROJECT_NAME:-peach}"
BUILD_CONTEXT="${ROOT}/backend"
if [[ "${LOCAL_RELEASE:-0}" == 1 ]]; then
  SNAPSHOT="$(python3 "${ROOT}/scripts/backend-snapshot.py")"
  BUILD_CONTEXT="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["directory"])' <<< "${SNAPSHOT}")"
  SHA="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["tag"])' <<< "${SNAPSHOT}")"
else
  SHA="$(git -C "${ROOT}" rev-parse HEAD)"
  git -C "${ROOT}" diff --quiet HEAD -- backend || { echo 'Commit backend changes first or use LOCAL_RELEASE=1'; exit 1; }
  [[ -z "$(git -C "${ROOT}" ls-files --others --exclude-standard backend)" ]] || { echo 'Commit backend files first or use LOCAL_RELEASE=1'; exit 1; }
fi
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
REPO="${PROJECT_NAME}-agenda-parser"
REGISTRY="${ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com"
if ! aws ecr describe-repositories --repository-names "${REPO}" >/dev/null 2>&1; then
  aws ecr create-repository --repository-name "${REPO}" --image-tag-mutability IMMUTABLE \
    --image-scanning-configuration scanOnPush=true --tags "Key=PROJECT_NAME,Value=${PROJECT_NAME}" >/dev/null
fi
if ! aws ecr describe-images --repository-name "${REPO}" --image-ids "imageTag=${SHA}" >/dev/null 2>&1; then
  aws ecr get-login-password | docker login --username AWS --password-stdin "${REGISTRY}" >/dev/null
  docker buildx build --platform linux/arm64 --target lambda --provenance=false --sbom=false \
    --tag "${REGISTRY}/${REPO}:${SHA}" --push "${BUILD_CONTEXT}"
fi
DIGEST="$(aws ecr describe-images --repository-name "${REPO}" --image-ids "imageTag=${SHA}" --query 'imageDetails[0].imageDigest' --output text)"
output() {
  aws cloudformation describe-stacks --stack-name "${PROJECT_NAME}-cognito" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text
}
# Keep the email out of command-line arguments and deployment logs.
PARAM_FILE="$(mktemp)"
trap 'rm -f "${PARAM_FILE}"' EXIT
chmod 600 "${PARAM_FILE}"
export AI_IMAGE_URI="${REGISTRY}/${REPO}@${DIGEST}" AI_POOL="$(output UserPoolId)" AI_CLIENT="$(output ClientId)" PROJECT_NAME
python3 - "${PARAM_FILE}" <<'PY'
import json, os, sys
params = {'ProjectName': os.environ['PROJECT_NAME'], 'ImageUri': os.environ['AI_IMAGE_URI'],
          'CognitoUserPoolId': os.environ['AI_POOL'], 'CognitoClientId': os.environ['AI_CLIENT'],
          'SiteOrigin': os.environ['SITE_URL'].rstrip('/'), 'BudgetEmail': os.environ['BUDGET_EMAIL'],
          'ParserModel': os.environ.get('PARSER_MODEL', 'amazon.nova-pro-v1:0'),
          'InputPrice': os.environ.get('PARSER_INPUT_USD_PER_MILLION', '0.8'),
          'OutputPrice': os.environ.get('PARSER_OUTPUT_USD_PER_MILLION', '3.2')}
with open(sys.argv[1], 'w') as f:
    json.dump([{'ParameterKey': k, 'ParameterValue': v} for k, v in params.items()], f)
PY
aws cloudformation deploy --stack-name "${PROJECT_NAME}-ai" --template-file "${ROOT}/infra/ai.yml" \
  --parameter-overrides "file://${PARAM_FILE}" --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset --tags "PROJECT_NAME=${PROJECT_NAME}"
PARSER_URL="$(aws cloudformation describe-stacks --stack-name "${PROJECT_NAME}-ai" --query "Stacks[0].Outputs[?OutputKey=='ParserUrl'].OutputValue" --output text)"
PARSER_URL="${PARSER_URL}" python3 - "${ROOT}/.env" <<'PY'
import os, pathlib, sys
p = pathlib.Path(sys.argv[1])
lines = [line for line in p.read_text().splitlines() if not line.startswith('NEXT_PUBLIC_AGENDA_PARSER_URL=')]
lines.append('NEXT_PUBLIC_AGENDA_PARSER_URL=' + os.environ['PARSER_URL'])
p.write_text('\n'.join(lines) + '\n')
PY
echo "Parser deployed: ${PARSER_URL}"
