#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

SECRET_FILE="${TRADING_SCANNER_SECRET_FILE:-$HOME/.config/trading-scanner/env}"

if [ -f "$SECRET_FILE" ]; then
    set -a
    . "$SECRET_FILE"
    set +a
fi

if [ "${1:-}" = "--check-env" ]; then
    : "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY is not set}"
    echo "DEEPSEEK_API_KEY=AVAILABLE"
    exit 0
fi

: "${DEEPSEEK_API_KEY:?DEEPSEEK_API_KEY is not set}"

exec .venv/bin/python -m engine.run_validated_dry_v4
