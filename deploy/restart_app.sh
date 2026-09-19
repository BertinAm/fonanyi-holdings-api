#!/bin/bash
# Restart the Passenger app without opening cPanel.
# Passenger watches tmp/restart.txt and recycles workers when its mtime changes.
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$APP_DIR/tmp"
touch "$APP_DIR/tmp/restart.txt"
echo "Restart requested for $APP_DIR"
