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

import re
import subprocess
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

# cPanel writes its own passenger_wsgi.py whenever the Python app is edited.
# Its stub imports itself and dies on RecursionError, which Passenger reports
# only as a 500, so the real file goes back before anything else runs.
STUB_MARKER = "load_source"

HTACCESS_BEGIN = "# BEGIN fonanyi source protection"
HTACCESS_END = "# END fonanyi source protection"
# Kept in one file so this and deploy/harden_htaccess.sh cannot drift apart.
HTACCESS_RULES_FILE = APP_DIR / "deploy" / "htaccess_rules.txt"

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
    if not HTACCESS_RULES_FILE.is_file():
        print(f"    {HTACCESS_RULES_FILE} is missing; left alone", flush=True)
        failures.append("htaccess rules file missing")
        return

    path = APP_DIR / ".htaccess"
    existing = path.read_text() if path.is_file() else ""

    # An existing block is replaced rather than skipped, so a change to the
    # rules actually reaches a host that was hardened by an earlier version.
    if HTACCESS_BEGIN in existing:
        pattern = re.compile(
            rf"^{re.escape(HTACCESS_BEGIN)}.*?^{re.escape(HTACCESS_END)}\n?",
            re.DOTALL | re.MULTILINE,
        )
        existing = pattern.sub("", existing)
        print("    replaced the previous block", flush=True)

    # Appended, never replacing the whole file: cPanel owns the Passenger
    # directives at the top and rewrites them whenever the app is edited.
    path.write_text(existing.rstrip("\n") + "\n\n" + HTACCESS_RULES_FILE.read_text())
    print("    rules written", flush=True)


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
