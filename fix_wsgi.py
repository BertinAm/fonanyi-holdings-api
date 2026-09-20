"""Restore passenger_wsgi.py after cPanel has overwritten it with its stub.

Creating or recreating a Python app makes cPanel write its own
passenger_wsgi.py into the application root. With the checkout and the app
root being the same directory, that lands on top of the repository's copy.

cPanel's stub calls load_source('wsgi', 'passenger_wsgi.py') -- it loads
itself, recurses until Python gives up, and Passenger returns a 500.

Run this from cPanel's "Execute python script" box after any app create or
recreate. It restores the tracked file from git, so there is one source of
truth and this script cannot go stale.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGET = HERE / "passenger_wsgi.py"

current = TARGET.read_text() if TARGET.is_file() else ""
if "load_source" not in current and "get_wsgi_application" in current:
    print(f"  {TARGET} already looks correct ({len(current)} bytes). Nothing to do.")
    sys.exit(0)

print(f"  Found cPanel's stub ({len(current)} bytes). Restoring from git...")
result = subprocess.run(
    ["git", "-C", str(HERE), "checkout", "--", "passenger_wsgi.py"],
    capture_output=True, text=True,
)
if result.returncode != 0:
    print("  git checkout failed:", result.stderr.strip()[:300])
    sys.exit(1)

restored = TARGET.read_text()
ok = "get_wsgi_application" in restored and "load_source" not in restored
print(f"  Restored ({len(restored)} bytes). Looks correct: {ok}")
print("\n  Now click Restart in Setup Python App.")
sys.exit(0 if ok else 1)
