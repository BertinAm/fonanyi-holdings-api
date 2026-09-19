"""Idempotent replay for POST endpoints that must be safe to retry.

A flaky connection on the login form is the common case: the browser resends
the request, the first one actually succeeded, and the user either burns a
throttle slot or ends up with a second token pair issued for the same intent.
A client that sends an `Idempotency-Key` header gets the first response back
verbatim instead.

The cache key deliberately mixes in a hash of the request body. That means a
key can only retrieve a response for the exact credentials that produced it,
so knowing (or guessing) somebody else's key is not enough to be handed their
token. It also stops a client reusing one key for two different logins.
"""
import hashlib
import json

from django.core.cache import cache
from rest_framework.response import Response

HEADER = "HTTP_IDEMPOTENCY_KEY"
KEY_MAX_LENGTH = 200
# Long enough to cover a retry cycle, short enough that a captured key is
# not a lasting credential.
TTL_SECONDS = 300


def _fingerprint(request) -> str:
    body = request.body or b""
    return hashlib.sha256(body).hexdigest()


def cache_key(request, scope: str) -> str | None:
    """None when the caller did not ask for idempotency, or the key is unusable."""
    raw = request.META.get(HEADER, "").strip()
    if not raw or len(raw) > KEY_MAX_LENGTH:
        return None
    # The client's key is hashed rather than interpolated, so it cannot shape
    # the cache key or collide with another scope's namespace.
    digest = hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()
    return f"idem:{scope}:{digest}:{_fingerprint(request)}"


def replay(key: str | None) -> Response | None:
    if not key:
        return None
    try:
        stored = cache.get(key)
    except Exception:
        # Idempotency is a convenience, never a precondition. If the cache
        # backend is unreachable (or its table was never created on a fresh
        # deploy) the request must still be allowed through as a normal login
        # rather than failing closed.
        return None
    if stored is None:
        return None
    response = Response(json.loads(stored["body"]), status=stored["status"])
    response["Idempotent-Replay"] = "true"
    return response


def remember(key: str | None, response: Response) -> None:
    """Only successful responses are stored.

    Caching a failure would let one bad attempt pin an error in place for the
    whole window, and would hide a password that started working in between.
    """
    if not key or not (200 <= response.status_code < 300):
        return
    try:
        cache.set(
            key,
            {"status": response.status_code, "body": json.dumps(response.data)},
            TTL_SECONDS,
        )
    except Exception:
        # Same reasoning as replay(): losing the record only means the next
        # retry is handled as a fresh login.
        pass
