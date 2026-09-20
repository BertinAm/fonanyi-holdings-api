#!/bin/bash
# The application root and the document root are the same directory, which is
# what makes Passenger work on this host -- and also means LiteSpeed will hand
# out any file in the checkout that a URL happens to name. /manage.py and
# /config/settings.py both answered 200 before this ran.
#
# cPanel owns the top of .htaccess (the Passenger directives) and rewrites it
# whenever the Python app is edited, so this appends a marked block rather than
# replacing the file, and re-appends it if cPanel has dropped it.
#
# The rules themselves live in deploy/htaccess_rules.txt, so this script and
# deploy/run_deploy.py cannot drift apart.
set -euo pipefail

APP_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
FILE="$APP_DIR/.htaccess"
RULES="$APP_DIR/deploy/htaccess_rules.txt"
BEGIN="# BEGIN fonanyi source protection"
END="# END fonanyi source protection"

if [[ ! -f "$RULES" ]]; then
  echo "==> $RULES is missing; leaving .htaccess alone" >&2
  exit 1
fi

# An existing block is removed rather than skipped, so a change to the rules
# actually reaches a host that was hardened by an earlier version.
if [[ -f "$FILE" ]] && grep -qF "$BEGIN" "$FILE"; then
  sed -i.bak "/^${BEGIN}/,/^${END}/d" "$FILE"
  rm -f "$FILE.bak"
  echo "==> Removed the previous source-protection block"
fi

printf '\n' >> "$FILE"
cat "$RULES" >> "$FILE"
echo "==> Source-protection rules written to .htaccess"
