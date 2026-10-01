#!/usr/bin/env bash
# .env is local configuration; backticks inside JMESPath queries are literals.
# shellcheck disable=SC1091,SC2016
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT}/.env" ]]; then
  preset="$(export -p)"; set -a; source "${ROOT}/.env"; set +a; eval "${preset}"
fi
for var in AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN; do
  [[ -n "${!var:-}" ]] || unset "${var}"
done
export AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-peach}"
STACK="${ECS_STACK_NAME:-${PROJECT_NAME}-ecs-backend}"
case "${1:-}" in
  logs)
    aws logs tail "/ecs/${PROJECT_NAME}-backend" --follow --since 10m
    ;;
  destroy)
    echo "Deletes ECS, ALB, and ECS logs from ${STACK}. Aurora and the legacy Lambda remain."
    read -r -p "Type the stack name to confirm: " reply
    [[ "${reply}" == "${STACK}" ]] || exit 1
    aws cloudformation delete-stack --stack-name "${STACK}"
    aws cloudformation wait stack-delete-complete --stack-name "${STACK}"
    echo "ECS stack removed. ECR images remain in ${PROJECT_NAME}-ecs-backend."
    ;;
  *) echo 'Usage: ecs-admin.sh logs|destroy' >&2; exit 1 ;;
esac
