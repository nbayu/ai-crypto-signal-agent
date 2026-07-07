#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

: "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY is not set}"

exec .venv/bin/python -m engine.run_validated_dry_v4
