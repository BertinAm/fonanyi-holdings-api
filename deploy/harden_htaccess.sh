#!/bin/bash
# The application root and the document root are the same directory, which is
# what makes Passenger work on this host -- and also means LiteSpeed will hand
# out any file in the checkout that a URL happens to name. /manage.py and
# /config/settings.py both answered 200 before this ran.
#
# cPanel owns the top of .htaccess (the Passenger directives) and rewrites it
# whenever the Python app is edited, so this appends a marked block rather than
# replacing the file, and re-appends it if cPanel has dropped it.
set -euo pipefail

APP_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
FILE="$APP_DIR/.htaccess"
MARKER="# BEGIN fonanyi source protection"

if [[ -f "$FILE" ]] && grep -qF "$MARKER" "$FILE"; then
  echo "==> .htaccess already hardened"
  exit 0
fi

cat >> "$FILE" <<'RULES'

# BEGIN fonanyi source protection
# Only /static/ and /media/ are meant to be fetched off the disk. Everything
# else in this directory is application source and belongs to Passenger.
<FilesMatch "\.(py|pyc|pyo|yml|yaml|sh|md|cfg|ini|toml|log|sqlite3|example|lock)$">
  Require all denied
</FilesMatch>

# Dotfiles, but only by their own name. Apache matches the last path segment,
# so this does not touch anything inside /.well-known/.
<FilesMatch "^\.">
  Require all denied
</FilesMatch>

RedirectMatch 404 ^/(config|apps|deploy|tests|docs|seed_media|tmp|\.git)(/|$)
# END fonanyi source protection
RULES

echo "==> Appended source-protection rules to .htaccess"
