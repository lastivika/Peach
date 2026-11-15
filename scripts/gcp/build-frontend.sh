#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
: "${NEXT_PUBLIC_API_URL:?Set the verified Cloud Run HTTPS URL}"
: "${NEXT_PUBLIC_COGNITO_REGION:?Set the existing Cognito region}"
: "${NEXT_PUBLIC_COGNITO_USER_POOL_ID:?Set the existing Cognito pool}"
: "${NEXT_PUBLIC_COGNITO_CLIENT_ID:?Set the existing Cognito client}"
: "${NEXT_PUBLIC_COGNITO_DOMAIN:?Set the existing Cognito hosted login domain}"
[[ "$NEXT_PUBLIC_API_URL" == https://* ]] || { echo 'API URL must use HTTPS' >&2; exit 1; }
# Explicit empty disables optional AI; avoids inheriting a local AWS parser URL.
export NEXT_PUBLIC_AGENDA_PARSER_URL="${NEXT_PUBLIC_AGENDA_PARSER_URL:-}"
export NEXT_OUTPUT=export
cd "$ROOT/frontend"
pnpm install --frozen-lockfile
pnpm exec next build --webpack
for page in index login callback auth/callback items calendar home; do
  [[ -f "out/$page.html" ]] || { echo "Missing exported route: $page" >&2; exit 1; }
done
