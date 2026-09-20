"""Why isn't Passenger starting? Checks the three things left."""
import os, stat, subprocess, sys

HOME = os.path.expanduser("~")
APP = os.path.join(HOME, "fonanyi-api")

def head(t): print("\n" + "=" * 62 + "\n  " + t + "\n" + "=" * 62)

head("1. INODES AND DISK  (exhaustion = silent Passenger failure)")
try:
    s = os.statvfs(HOME)
    if s.f_files:
        used = s.f_files - s.f_ffree
        print(f"  inodes used   : {used:,} of {s.f_files:,}  ({used/s.f_files*100:.1f}%)")
        print(f"  inodes free   : {s.f_ffree:,}")
    else:
        print("  inode counters not exposed by this filesystem")
    gb = lambda b: b / 1024**3
    print(f"  disk used     : {gb((s.f_blocks-s.f_bfree)*s.f_frsize):.2f} GB "
          f"of {gb(s.f_blocks*s.f_frsize):.2f} GB")
    print(f"  disk free     : {gb(s.f_bavail*s.f_frsize):.2f} GB")
except Exception as e:
    print("  statvfs failed:", e)

for cmd in (["quota", "-s"], ["df", "-i", HOME]):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout.strip()
        if out:
            print(f"\n  $ {' '.join(cmd)}")
            for line in out.splitlines():
                print("    " + line)
    except Exception:
        pass

head("2. CAN WE ACTUALLY CREATE FILES?  (the decisive quota test)")
for label, path in (("app root", APP), ("app tmp", os.path.join(APP, "tmp")),
                    ("app public", os.path.join(APP, "public")), ("home", HOME)):
    probe = os.path.join(path, ".diag_probe")
    try:
        with open(probe, "w") as fh:
            fh.write("x" * 128)
        os.remove(probe)
        print(f"  {label:12} WRITE OK")
    except Exception as e:
        print(f"  {label:12} *** FAILED: {type(e).__name__}: {e} ***")

head("3. PERMISSIONS  (Passenger refuses group/world-writable, silently)")
targets = [HOME, APP,
           os.path.join(APP, "passenger_wsgi.py"),
           os.path.join(APP, "public"),
           os.path.join(APP, "tmp"),
           os.path.join(APP, ".env"),
           os.path.join(HOME, "api.fonanyiholdingsltd.com"),
           os.path.join(HOME, "api.fonanyiholdingsltd.com", ".htaccess"),
           os.path.join(HOME, "virtualenv", "fonanyi-api", "3.12", "bin", "python")]
for p in targets:
    try:
        st = os.stat(p)
        mode = stat.S_IMODE(st.st_mode)
        warn = ""
        if mode & stat.S_IWGRP: warn += "  <-- GROUP-WRITABLE"
        if mode & stat.S_IWOTH: warn += "  <-- WORLD-WRITABLE"
        print(f"  {oct(mode)[-4:]}  uid={st.st_uid}  {p}{warn}")
    except FileNotFoundError:
        print(f"  ----  MISSING            {p}")
    except Exception as e:
        print(f"  ----  {type(e).__name__}  {p}")

head("4. WHAT PASSENGER WOULD LOAD")
print(f"  interpreter running this : {sys.executable}")
print(f"  app root exists          : {os.path.isdir(APP)}")
wsgi = os.path.join(APP, "passenger_wsgi.py")
if os.path.isfile(wsgi):
    print(f"  passenger_wsgi.py size   : {os.path.getsize(wsgi)} bytes")
    with open(wsgi) as fh:
        first = [l.rstrip() for l in fh][:3]
    print("  first lines              :", " | ".join(first))
for name in ("stderr.log", "tmp/restart.txt"):
    p = os.path.join(APP, name)
    print(f"  {name:22}   {'exists' if os.path.exists(p) else 'absent'}")

head("5. INODE HOGS UNDER HOME")
try:
    counts = []
    for entry in os.scandir(HOME):
        if entry.is_dir(follow_symlinks=False):
            n = 0
            for _, dirs, files in os.walk(entry.path):
                n += len(dirs) + len(files)
                if n > 400000: break
            counts.append((n, entry.name))
    for n, name in sorted(counts, reverse=True)[:8]:
        print(f"  {n:>9,}  {name}")
except Exception as e:
    print("  walk failed:", e)
