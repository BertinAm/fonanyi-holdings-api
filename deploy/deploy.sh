#!/bin/bash
# Run after pulling new code in cPanel -> Git Version Control.
#
#   cd ~/fonanyi-api && bash deploy/deploy.sh
#
# Safe to re-run. It never touches .env, media/ or the database contents.
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

# cPanel creates the virtualenv under ~/virtualenv/<app-dir>/<python-version>,
# where <app-dir> is the Application root -- now the domain directory, since
# the checkout, the app root and the document root are all the same place.
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
# Belt and braces: the deploy task sets this too, but deploy.sh is also run
# by hand, and a 0700 app root stops Passenger starting without saying so.
if [[ "$(stat -c '%a' "$APP_DIR" 2>/dev/null || echo '')" == "700" ]]; then
  echo "==> App root was 0700; Passenger cannot traverse it. Fixing to 0755."
  chmod 0755 "$APP_DIR"
fi

# cPanel writes its own passenger_wsgi.py whenever the app is created, and
# with the checkout and the app root being one directory that overwrites ours.
# Its stub loads itself and dies on RecursionError, which Passenger reports
# only as a 500. Put the tracked file back before doing anything else.
if grep -q "load_source" "$APP_DIR/passenger_wsgi.py" 2>/dev/null; then
  echo "==> passenger_wsgi.py was replaced by cPanel's stub; restoring from git"
  git -C "$APP_DIR" checkout -- passenger_wsgi.py || true
fi

echo "==> Installing dependencies"
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -r requirements-shared-hosting.txt

echo "==> Applying database migrations"
"$PY" manage.py migrate --noinput

# Backs the login endpoint's Idempotency-Key replay. Re-running this is
# harmless: it reports that the table already exists and exits cleanly. Left
# out, login still works, it just quietly loses the ability to replay a retry.
echo "==> Ensuring the cache table exists"
"$PY" manage.py createcachetable

echo "==> Collecting static files"
"$PY" manage.py collectstatic --noinput

echo "==> Checking deployment settings"
"$PY" manage.py check --deploy || true

echo "==> Restarting Passenger"
mkdir -p tmp
touch tmp/restart.txt

echo "==> Done. Verify: curl -si https://\$API_DOMAIN/api/site-settings/ | head -1"
