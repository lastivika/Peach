#!/usr/bin/env bash
# Infrastructure is owned by HCP Terraform; never recreate the former stack.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec make -C "${ROOT}" infra-plan
