#!/bin/bash
# Run after pulling new code in cPanel -> Git Version Control.
#
#   cd ~/fonanyi-api && bash deploy/deploy.sh
#
# Safe to re-run. It never touches .env, media/ or the database contents.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

# cPanel creates the virtualenv under ~/virtualenv/<app-dir>/<python-version>.
# VENV_DIR can be exported to override the guess.
if [[ -z "${VENV_DIR:-}" ]]; then
  VENV_DIR="$(ls -d "$HOME"/virtualenv/"$(basename "$APP_DIR")"/*/ 2>/dev/null | head -1 || true)"
fi
if [[ -z "$VENV_DIR" || ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Could not find the virtualenv. Set VENV_DIR and re-run." >&2
  echo "Look under ~/virtualenv/ for the right path." >&2
  exit 1
fi

PY="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

echo "==> Using $PY"
echo "==> Installing dependencies"
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -r requirements-shared-hosting.txt

echo "==> Applying database migrations"
"$PY" manage.py migrate --noinput

echo "==> Collecting static files"
"$PY" manage.py collectstatic --noinput

echo "==> Checking deployment settings"
"$PY" manage.py check --deploy || true

echo "==> Restarting Passenger"
mkdir -p tmp
touch tmp/restart.txt

echo "==> Done. Verify: curl -si https://\$API_DOMAIN/api/site-settings/ | head -1"
