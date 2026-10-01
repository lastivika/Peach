#!/usr/bin/env bash
# .env is local configuration; backticks inside JMESPath queries are literals.
# shellcheck disable=SC1091,SC2016
# Request a regional certificate; publish the printed validation CNAME in your DNS provider.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT}/.env" ]]; then
  preset="$(export -p)"; set -a; source "${ROOT}/.env"; set +a; eval "${preset}"
fi
for var in AWS_PROFILE AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN; do
  [[ -n "${!var:-}" ]] || unset "${var}"
done
export AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
DOMAIN="${API_DOMAIN_NAME:?Set API_DOMAIN_NAME (e.g. api.example.com)}"
[[ "${DOMAIN}" =~ ^[a-zA-Z0-9.-]+$ ]] || { echo 'Invalid domain' >&2; exit 1; }
CALLER="$(aws sts get-caller-identity --query Arn --output text)"
[[ "${CALLER}" != *:root ]] || { echo 'Use a non-root IAM identity' >&2; exit 1; }
ARN="$(aws acm list-certificates --certificate-statuses PENDING_VALIDATION ISSUED \
  --query "CertificateSummaryList[?DomainName=='${DOMAIN}']|[0].CertificateArn" --output text)"
if [[ -z "${ARN}" || "${ARN}" == None ]]; then
  ARN="$(aws acm request-certificate --domain-name "${DOMAIN}" --validation-method DNS \
    --tags "Key=PROJECT_NAME,Value=${PROJECT_NAME:-peach}" --query CertificateArn --output text)"
fi
for _ in 1 2 3 4 5; do
  RECORD="$(aws acm describe-certificate --certificate-arn "${ARN}" --query 'Certificate.DomainValidationOptions[0].ResourceRecord' --output json)"
  [[ "${RECORD}" != null ]] && break
  sleep 2
done
printf 'API_CERTIFICATE_ARN=%s\nPublish this validation CNAME in DNS:\n%s\n' "${ARN}" "${RECORD}"
ARN="${ARN}" python3 - "${ROOT}/.env" <<'PY'
import os, pathlib, sys
p = pathlib.Path(sys.argv[1])
lines = p.read_text().splitlines() if p.exists() else []
lines = [s for s in lines if not s.startswith('API_CERTIFICATE_ARN=')]
p.write_text('\n'.join(lines + ['API_CERTIFICATE_ARN=' + os.environ['ARN']]) + '\n')
PY
aws acm describe-certificate --certificate-arn "${ARN}" --query Certificate.Status --output text
