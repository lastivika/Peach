#!/usr/bin/env bash
# .env is local configuration; backticks inside JMESPath queries are literals.
# shellcheck disable=SC1091,SC2016
# The local and CI deployment contract: immutable SHA image -> migration -> ECS rollout.
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
die() { echo "error: $*" >&2; exit 1; }
for tool in aws docker python3 git; do
  command -v "${tool}" >/dev/null || die "${tool} is required"
done
PROJECT_NAME="${PROJECT_NAME:-peach}"
export AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
STACK="${ECS_STACK_NAME:-${PROJECT_NAME}-ecs-backend}"
DATABASE_STACK="${DATABASE_STACK_NAME:-${PROJECT_NAME}-backend}"
REPOSITORY="${PROJECT_NAME}-ecs-backend"
API_CORS_ORIGINS="${API_CORS_ORIGINS:?Set the deployed frontend HTTPS origin}"
[[ "${API_CORS_ORIGINS}" != '*' ]] || die "Set API_CORS_ORIGINS to the frontend origin"
CALLER="$(aws sts get-caller-identity --query Arn --output text)"
[[ "${CALLER}" != *:root ]] || die "Use a non-root IAM user/role for the lab deployment"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"

output() {
  aws cloudformation describe-stacks --stack-name "$1" \
    --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text
}
CF_PREFIX_LIST="$(aws ec2 describe-managed-prefix-lists --filters Name=prefix-list-name,Values=com.amazonaws.global.cloudfront.origin-facing --query 'PrefixLists[0].PrefixListId' --output text)"
COGNITO_USER_POOL_ID="${COGNITO_USER_POOL_ID:-$(output "${PROJECT_NAME}-cognito" UserPoolId)}"
COGNITO_CLIENT_ID="${COGNITO_CLIENT_ID:-$(output "${PROJECT_NAME}-cognito" ClientId)}"
# Reuse the existing Aurora database; no data is copied or destroyed during migration to ECS.
DATABASE_URL_SECRET_ARN="${DATABASE_URL_SECRET_ARN:-$(output "${DATABASE_STACK}" DatabaseUrlSecretArn)}"
DATABASE_SECURITY_GROUP_ID="${DATABASE_SECURITY_GROUP_ID:-$(aws cloudformation describe-stack-resource \
  --stack-name "${DATABASE_STACK}" --logical-resource-id DbSecurityGroup \
  --query StackResourceDetail.PhysicalResourceId --output text)}"
AWS_VPC_ID="${AWS_VPC_ID:-$(aws ec2 describe-security-groups --group-ids "${DATABASE_SECURITY_GROUP_ID}" --query 'SecurityGroups[0].VpcId' --output text)}"
AWS_SUBNET_IDS="${AWS_SUBNET_IDS:-$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=${AWS_VPC_ID}" Name=default-for-az,Values=true --query 'Subnets[].SubnetId' --output text | tr '\t' ',')}"
[[ "${AWS_SUBNET_IDS}" == *,* ]] || die "Set public subnets in at least two availability zones"

IMAGE_TAG="${IMAGE_TAG:-${GITHUB_SHA:-$(git -C "${ROOT}" rev-parse HEAD)}}"
[[ "${IMAGE_TAG}" =~ ^[0-9a-f]{40}$ ]] || die "IMAGE_TAG must be a full Git commit SHA, never latest"
REGISTRY="${ACCOUNT}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com"
IMAGE_URI="${REGISTRY}/${REPOSITORY}:${IMAGE_TAG}"
if ! aws ecr describe-repositories --repository-names "${REPOSITORY}" >/dev/null 2>&1; then
  aws ecr create-repository --repository-name "${REPOSITORY}" \
    --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true \
    --tags "Key=PROJECT_NAME,Value=${PROJECT_NAME}" >/dev/null
fi
if ! aws ecr describe-images --repository-name "${REPOSITORY}" --image-ids "imageTag=${IMAGE_TAG}" >/dev/null 2>&1; then
  [[ "${IMAGE_TAG}" == "$(git -C "${ROOT}" rev-parse HEAD)" ]] || die "For rollback the previous SHA must already exist in ECR"
  git -C "${ROOT}" diff --quiet HEAD -- backend || die "Commit backend changes before deploying a SHA-tagged image"
  [[ -z "$(git -C "${ROOT}" ls-files --others --exclude-standard backend)" ]] || die "Commit untracked backend files before deploying"
  aws ecr get-login-password | docker login --username AWS --password-stdin "${REGISTRY}" >/dev/null
  docker buildx build --platform linux/arm64 --target runtime --provenance=false --sbom=false \
    --tag "${IMAGE_URI}" --push "${ROOT}/backend"
fi

# Keep the running service pinned to its previous release while preparing a new task revision.
PARAMS=("ProjectName=${PROJECT_NAME}" "VpcId=${AWS_VPC_ID}" "SubnetIds=${AWS_SUBNET_IDS}"
  "DatabaseSecurityGroupId=${DATABASE_SECURITY_GROUP_ID}" "DatabaseUrlSecretArn=${DATABASE_URL_SECRET_ARN}"
  "ImageUri=${IMAGE_URI}" "CloudFrontPrefixListId=${CF_PREFIX_LIST}"
  "CognitoUserPoolId=${COGNITO_USER_POOL_ID}" "CognitoClientId=${COGNITO_CLIENT_ID}"
  "CorsOrigins=${API_CORS_ORIGINS}")
deploy() {
  aws cloudformation deploy --stack-name "${STACK}" --template-file "${ROOT}/infra/ecs-backend.yaml" \
    --parameter-overrides "${PARAMS[@]}" "$@" --capabilities CAPABILITY_NAMED_IAM \
    --no-fail-on-empty-changeset --tags "PROJECT_NAME=${PROJECT_NAME}"
}
deploy
CLUSTER="$(output "${STACK}" ClusterName)"
SERVICE="$(output "${STACK}" ServiceName)"
TASK_DEFINITION="$(output "${STACK}" TaskDefinitionArn)"
SECURITY_GROUP="$(output "${STACK}" TaskSecurityGroupId)"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "${TEMP_DIR}"' EXIT
SUBNETS="${AWS_SUBNET_IDS}" SECURITY_GROUP="${SECURITY_GROUP}" python3 - "${TEMP_DIR}/network.json" <<'PY'
import json, os, sys
with open(sys.argv[1], 'w') as f:
    json.dump({'awsvpcConfiguration': {'subnets': os.environ['SUBNETS'].split(','),
              'securityGroups': [os.environ['SECURITY_GROUP']], 'assignPublicIp': 'ENABLED'}}, f)
PY
# Exactly one migration task. Do not promote the service if the task fails.
aws ecs run-task --cluster "${CLUSTER}" --launch-type FARGATE --task-definition "${TASK_DEFINITION}" \
  --network-configuration "file://${TEMP_DIR}/network.json" \
  --overrides '{"containerOverrides":[{"name":"api","command":["alembic","upgrade","head"]}]}' \
  --output json > "${TEMP_DIR}/migration.json"
TASK_ARN="$(python3 - "${TEMP_DIR}/migration.json" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
if r.get('failures') or not r.get('tasks'):
    raise SystemExit('Migration task could not start: ' + str(r.get('failures')))
print(r['tasks'][0]['taskArn'])
PY
)"
aws ecs wait tasks-stopped --cluster "${CLUSTER}" --tasks "${TASK_ARN}"
EXIT_CODE="$(aws ecs describe-tasks --cluster "${CLUSTER}" --tasks "${TASK_ARN}" --query 'tasks[0].containers[?name==`api`].exitCode | [0]' --output text)"
[[ "${EXIT_CODE}" == 0 ]] || die "Migration failed (${EXIT_CODE}); inspect /ecs/${PROJECT_NAME}-backend logs. Existing release was not promoted."
deploy "ReleaseTaskDefinition=${TASK_DEFINITION}" "DesiredCount=${ECS_DESIRED_COUNT:-1}"
aws ecs wait services-stable --cluster "${CLUSTER}" --services "${SERVICE}"
LIVE_TASK="$(aws ecs describe-services --cluster "${CLUSTER}" --services "${SERVICE}" --query 'services[0].taskDefinition' --output text)"
[[ "${LIVE_TASK}" == "${TASK_DEFINITION}" ]] || die "ECS rolled back the release; inspect service events"
API_URL="$(output "${STACK}" ApiUrl)"
echo "API: ${API_URL}"
echo "DNS routing target: $(output "${STACK}" AlbDnsName)"
curl --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 5 --max-time 45 "${API_URL}/api/v1/health/ready"
# Save only after verifying DNS, HTTPS, the app and its database.
API_URL="${API_URL}" python3 - "${ROOT}/.env" <<'PY'
import os, pathlib, sys
p = pathlib.Path(sys.argv[1])
lines = p.read_text().splitlines() if p.exists() else []
lines = [line for line in lines if not line.startswith('BACKEND_URL=')]
lines.append('BACKEND_URL=' + os.environ['API_URL'])
p.write_text('\n'.join(lines) + '\n')
PY
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "backend_url=${API_URL}" >> "${GITHUB_OUTPUT}"
fi
echo "Deployed ${IMAGE_TAG} to ECS."
