"""Cleaning for anything the public can POST.

Django's field validation checks shape and length but leaves the contents
alone, so a submission can still carry control characters, bidi overrides or
a megabyte of whitespace. These helpers normalise the text before it reaches
the database and the dashboard.
"""
import ipaddress
import re
import unicodedata

from django.conf import settings

# Runs of blank lines, and trailing spaces on a line.
_BLANK_RUN = re.compile(r"\n{3,}")
_TRAILING_WS = re.compile(r"[ \t]+\n")
_WS_RUN = re.compile(r"\s+")


def _scrub(value: str, keep_newlines: bool) -> str:
    """Drop characters that have no business in submitted text.

    Cc is the C0/C1 control block. Cf is the format block, which holds the
    zero-width characters and the bidi overrides used to make a string render
    as something other than what it stores. Cs and Co are surrogates and
    private-use characters, which only arrive from broken encoders.
    """
    out = []
    for ch in value:
        category = unicodedata.category(ch)
        if category == "Cc":
            # clean_text folds CR into LF before calling this, so the only
            # controls worth keeping here are the ones a body legitimately
            # contains. clean_line keeps none, which is what stops a CR or LF
            # in a name or subject becoming header injection downstream.
            if keep_newlines and ch in "\n\t":
                out.append(ch)
            continue
        if category in {"Cf", "Cs", "Co"}:
            continue
        out.append(ch)
    return "".join(out)


def clean_line(value: str | None) -> str:
    """For single-line fields: names, subjects, phone numbers, locations.

    Newlines are removed rather than preserved. A name or subject that still
    contains CR or LF is what turns into header injection the moment someone
    forwards one of these messages by email.
    """
    if not value:
        return ""
    value = unicodedata.normalize("NFC", value)
    # Line breaks are separators, so they collapse to a space rather than
    # being dropped, which would run the words on either side together.
    value = value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    value = _scrub(value, keep_newlines=False)
    return _WS_RUN.sub(" ", value).strip()


def clean_text(value: str | None) -> str:
    """For multi-line bodies: the message and the application write-up."""
    if not value:
        return ""
    value = unicodedata.normalize("NFC", value)
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = _scrub(value, keep_newlines=True)
    value = _TRAILING_WS.sub("\n", value)
    return _BLANK_RUN.sub("\n\n", value).strip()


def _valid_ip(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return str(ipaddress.ip_address(raw.strip()))
    except ValueError:
        return None


def client_ip(request) -> str | None:
    """The caller's address, or None when it cannot be established.

    These headers are attacker-controlled unless a proxy we trust is the one
    setting them, so they are only read when TRUST_PROXY_HEADER says we sit
    behind one. Anything that is not a parseable address returns None instead
    of being written through to a GenericIPAddressField, which would otherwise
    raise on save and turn a spoofed header into a 500.

    CF-Connecting-IP is preferred over X-Forwarded-For. Cloudflare sets it to
    exactly one address and overwrites any value the client sent, whereas
    X-Forwarded-For is a list the client can prepend to. Behind Cloudflare,
    REMOTE_ADDR is Cloudflare's own address for every visitor alike, so
    falling back to it makes every visitor look like the same one.
    """
    if getattr(settings, "TRUST_PROXY_HEADER", False):
        direct = _valid_ip(request.META.get("HTTP_CF_CONNECTING_IP"))
        if direct:
            return direct
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        for candidate in forwarded.split(","):
            ip = _valid_ip(candidate)
            if ip:
                return ip
    return _valid_ip(request.META.get("REMOTE_ADDR"))
