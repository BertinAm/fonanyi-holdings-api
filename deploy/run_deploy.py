#!/usr/bin/env python
"""Run the deployment from cPanel's "Execute python script" box.

Setup Python App has that box and this plan has no shell, so when the Git
Version Control page will not deploy -- the button greys out for reasons the
page does not always explain -- this is the way in. Enter:

    Script path : deploy/run_deploy.py
    Arguments   : (none)

It does exactly what deploy/deploy.sh does, in the same order, using the
interpreter cPanel already activated for the box. Every step is safe to
repeat, so running it twice is not a problem.

Pass --skip-pip to leave the installed packages alone, which is much faster
when only the application code has changed.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

# cPanel writes its own passenger_wsgi.py whenever the Python app is edited.
# Its stub imports itself and dies on RecursionError, which Passenger reports
# only as a 500, so the real file goes back before anything else runs.
STUB_MARKER = "load_source"

HTACCESS_MARKER = "# BEGIN fonanyi source protection"
HTACCESS_RULES = """
# BEGIN fonanyi source protection
# Only /static/ and /media/ are meant to be fetched off the disk. Everything
# else in this directory is application source and belongs to Passenger.
<FilesMatch "\\.(py|pyc|pyo|yml|yaml|sh|md|cfg|ini|toml|log|sqlite3|example|lock)$">
  Require all denied
</FilesMatch>

# Dotfiles, but only by their own name. Apache matches the last path segment,
# so this does not touch anything inside /.well-known/.
<FilesMatch "^\\.">
  Require all denied
</FilesMatch>

RedirectMatch 404 ^/(config|apps|deploy|tests|docs|seed_media|tmp|\\.git)(/|$)
# END fonanyi source protection
"""

failures: list[str] = []


def step(label: str, *argv: str, required: bool = True) -> bool:
    print(f"\n==> {label}", flush=True)
    result = subprocess.run(argv, cwd=APP_DIR)
    if result.returncode != 0:
        note = f"{label} (exit {result.returncode})"
        print(f"!!! {note}", flush=True)
        if required:
            failures.append(note)
        return False
    return True


def manage(label: str, *argv: str, required: bool = True) -> bool:
    return step(label, PYTHON, "manage.py", *argv, required=required)


def restore_wsgi() -> None:
    print("\n==> Checking passenger_wsgi.py", flush=True)
    path = APP_DIR / "passenger_wsgi.py"
    try:
        current = path.read_text()
    except OSError as error:
        print(f"    could not read it: {error}", flush=True)
        return
    if STUB_MARKER in current:
        print("    cPanel's stub is in place; restoring the tracked file", flush=True)
        subprocess.run(["git", "checkout", "--", "passenger_wsgi.py"], cwd=APP_DIR)
    else:
        print("    fine, left alone", flush=True)


def fix_app_root_mode() -> None:
    # A 0700 application root stops Passenger traversing into it, and it fails
    # without saying why.
    mode = APP_DIR.stat().st_mode & 0o777
    print(f"\n==> Application root is {oct(mode)}", flush=True)
    if mode == 0o700:
        print("    Passenger cannot traverse that; setting 0755", flush=True)
        APP_DIR.chmod(0o755)


def harden_htaccess() -> None:
    print("\n==> Source protection in .htaccess", flush=True)
    path = APP_DIR / ".htaccess"
    existing = path.read_text() if path.is_file() else ""
    if HTACCESS_MARKER in existing:
        print("    already there", flush=True)
        return
    # Appended, never replaced: cPanel owns the Passenger directives at the
    # top of this file and rewrites them whenever the Python app is edited.
    with path.open("a") as handle:
        handle.write(HTACCESS_RULES)
    print("    rules appended", flush=True)


def restart() -> None:
    print("\n==> Restarting Passenger", flush=True)
    (APP_DIR / "tmp").mkdir(exist_ok=True)
    (APP_DIR / "tmp" / "restart.txt").touch()
    print("    touched tmp/restart.txt", flush=True)


def main() -> int:
    skip_pip = "--skip-pip" in sys.argv
    print(f"Application : {APP_DIR}")
    print(f"Interpreter : {PYTHON}")

    restore_wsgi()
    fix_app_root_mode()

    if skip_pip:
        print("\n==> Skipping dependency install (--skip-pip)", flush=True)
    else:
        step(
            "Installing dependencies",
            PYTHON, "-m", "pip", "install", "--quiet",
            "-r", "requirements-shared-hosting.txt",
        )

    manage("Applying database migrations", "migrate", "--noinput")
    # Backs the login endpoint's Idempotency-Key replay. Reporting that the
    # table already exists is a success, not a failure.
    manage("Ensuring the cache table exists", "createcachetable", required=False)
    manage("Collecting static files", "collectstatic", "--noinput")
    manage("Restoring any missing media files", "restore_media")
    manage("Checking deployment settings", "check", "--deploy", required=False)

    harden_htaccess()
    restart()

    if failures:
        print("\nFinished with problems:", flush=True)
        for note in failures:
            print(f"  - {note}", flush=True)
        return 1

    print("\nDone. Give Passenger a few seconds, then reload the API.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
