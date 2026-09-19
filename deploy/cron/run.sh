#!/bin/bash
# Shared wrapper for every cron entry.
#   Usage: bash deploy/cron/run.sh <manage.py command> [args...]
# Cron on cPanel runs with a bare environment, so everything is resolved here.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$APP_DIR"

if [[ -z "${VENV_DIR:-}" ]]; then
  VENV_DIR="$(ls -d "$HOME"/virtualenv/"$(basename "$APP_DIR")"/*/ 2>/dev/null | head -1 || true)"
fi
[[ -x "$VENV_DIR/bin/python" ]] || { echo "virtualenv not found" >&2; exit 1; }

mkdir -p logs
exec "$VENV_DIR/bin/python" manage.py "$@" >> "logs/cron-$1.log" 2>&1
