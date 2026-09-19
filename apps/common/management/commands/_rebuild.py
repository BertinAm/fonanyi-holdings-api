"""Ping the Cloudflare Pages deploy hook so the static site picks up new content.

Called from cron rather than from a web request: outbound HTTPS on shared
hosting is slow enough to time out a Passenger worker.
"""
import json
import urllib.request

from django.conf import settings


def request_rebuild(stdout=None):
    hook = getattr(settings, "CLOUDFLARE_DEPLOY_HOOK", "")
    if not hook:
        if stdout:
            stdout.write("CLOUDFLARE_DEPLOY_HOOK not set; skipping rebuild.")
        return False
    req = urllib.request.Request(hook, data=json.dumps({}).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            ok = 200 <= resp.status < 300
    except Exception as exc:  # pragma: no cover - network
        if stdout:
            stdout.write(f"Rebuild hook failed: {exc}")
        return False
    if stdout:
        stdout.write("Cloudflare rebuild requested." if ok else "Rebuild hook returned an error.")
    return ok
