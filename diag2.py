"""Does the request reach this box, and which document root is live?

The previous diagnostic only proved the machine is healthy, which was never
in doubt. This answers two things a local script genuinely can:

  * it plants a marker file in each candidate document root, so an external
    request can say which one the web server is serving
  * it reads the account's own access logs, which is the one local record of
    whether a request arrived at all
"""
import os, subprocess, time

HOME = os.path.expanduser("~")
DOMAIN = "api.fonanyiholdingsltd.com"
ROOTS = {
    "A": os.path.join(HOME, DOMAIN),
    "B": os.path.join(HOME, "fonanyi-api", "public"),
}

def head(t): print("\n" + "=" * 62 + "\n  " + t + "\n" + "=" * 62)

head("1. PLANTING MARKERS")
for tag, root in ROOTS.items():
    path = os.path.join(root, "marker.txt")
    try:
        os.makedirs(root, exist_ok=True)
        with open(path, "w") as fh:
            fh.write(tag + "\n")
        print(f"  {tag}  written to {path}")
    except Exception as e:
        print(f"  {tag}  FAILED {path}: {type(e).__name__}: {e}")

head("2. EVERY .htaccess UNDER HOME (which one is actually live?)")
for dirpath, dirnames, filenames in os.walk(HOME):
    depth = dirpath[len(HOME):].count(os.sep)
    if depth >= 4:
        dirnames[:] = []
        continue
    dirnames[:] = [d for d in dirnames if d not in
                   {"virtualenv", ".cagefs", ".cache", "node_modules", ".git", "mail"}]
    if ".htaccess" in filenames:
        p = os.path.join(dirpath, ".htaccess")
        try:
            body = open(p, encoding="utf-8", errors="replace").read()
        except Exception as e:
            print(f"\n  {p}  (unreadable: {e})")
            continue
        has_psgr = "PassengerAppRoot" in body
        in_ifmod = "mod_passenger" in body
        print(f"\n  {p}")
        print(f"     PassengerAppRoot present : {has_psgr}")
        print(f"     wrapped in <IfModule mod_passenger.c> : {in_ifmod}")
        print(f"     bytes: {len(body)}")
        for i, line in enumerate(body.splitlines()[:12], 1):
            print(f"       {i:>2}| {line!r}")

head("3. ACCESS LOGS  (did requests actually arrive?)")
found_any = False
for d in ("logs", "access-logs", "tmp/analog"):
    full = os.path.join(HOME, d)
    if os.path.isdir(full):
        found_any = True
        print(f"\n  {full}:")
        try:
            for name in sorted(os.listdir(full))[:40]:
                fp = os.path.join(full, name)
                try:
                    size = os.path.getsize(fp)
                except Exception:
                    size = -1
                print(f"    {size:>12,}  {name}")
        except Exception as e:
            print("    unreadable:", e)
if not found_any:
    print("  no logs/ or access-logs/ directory in home")

head("4. LAST LINES OF ANY LOG MENTIONING THIS DOMAIN")
shown = 0
for d in ("logs", "access-logs"):
    full = os.path.join(HOME, d)
    if not os.path.isdir(full):
        continue
    for name in sorted(os.listdir(full)):
        if DOMAIN not in name:
            continue
        fp = os.path.join(full, name)
        print(f"\n  --- {fp} ---")
        try:
            with open(fp, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                back = min(fh.tell(), 8000)
                fh.seek(-back, os.SEEK_END)
                tail = fh.read().decode("utf-8", "replace").splitlines()[-25:]
            for line in tail:
                print("    " + line[:200])
            shown += 1
        except Exception as e:
            print("    unreadable:", e)
if not shown:
    print("\n  No log file with this domain in its name.")
    print("  (cPanel rotates these; an empty or missing log does not by itself")
    print("   prove nothing arrived.)")

head("5. NOW FETCH THESE FROM OUTSIDE")
print(f"  https://{DOMAIN}/marker.txt")
print("     'A' -> document root is the domain folder")
print("     'B' -> document root is fonanyi-api/public")
print("     404 -> neither marker is being served")
