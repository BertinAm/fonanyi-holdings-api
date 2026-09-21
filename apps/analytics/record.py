"""Record an event without ever being the reason a request fails.

Analytics is the least important thing happening in any of these requests. A
contact form that saved the enquiry and then died writing a statistic would
be a far worse bug than a missing statistic, so everything here is wrapped
and logged rather than raised.
"""
from __future__ import annotations

import logging

from django.utils import timezone

from apps.common.sanitize import client_ip

from .models import VisitEvent

logger = logging.getLogger(__name__)


def record(request, kind, *, path="", label="", user=None):
    """Write one event. Returns the row, or None if it could not be written."""
    try:
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]
        ip = client_ip(request)
        return VisitEvent.objects.create(
            kind=kind,
            path=(path or request.path)[:300],
            label=label[:200],
            referrer=request.META.get("HTTP_REFERER", "")[:400],
            user_agent=user_agent,
            visitor_hash=VisitEvent.make_visitor_hash(ip, user_agent, timezone.now().date()),
            user=user if (user is not None and getattr(user, "pk", None)) else None,
        )
    except Exception:  # pragma: no cover - never worth failing the caller over
        logger.warning("Could not record a %s event", kind, exc_info=True)
        return None
