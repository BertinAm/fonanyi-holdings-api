import hashlib

from django.conf import settings
from django.db import models


class VisitEvent(models.Model):
    """One thing that happened on the site: a view, a click, a form, a login.

    No cookies and no raw IPs are stored: the visitor is identified by a
    salted daily hash, which is enough to count unique visitors without
    keeping personal data. The hash changes every day, so it cannot be used
    to follow somebody across dates.

    Anonymous traffic and staff activity share one table on purpose. They are
    read together -- "what happened this week" is one question, not two -- and
    a single table keeps the retention policy in one place, so pruning cannot
    quietly miss a second one.
    """

    PAGE = "page"
    LINK = "link"
    FORM = "form"
    LOGIN = "login"
    LOGIN_FAILED = "login_bad"

    KIND_CHOICES = [
        (PAGE, "Page view"),
        (LINK, "Link click"),
        (FORM, "Form submission"),
        (LOGIN, "Admin sign-in"),
        (LOGIN_FAILED, "Failed sign-in"),
    ]

    # Only these two may be reported by the public tracking endpoint. The
    # others are written by the server when it sees the thing happen, so that
    # a stranger cannot POST themselves a sign-in that never occurred.
    PUBLIC_KINDS = {PAGE, LINK}

    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=PAGE)
    path = models.CharField(max_length=300, db_index=True)
    label = models.CharField(max_length=200, blank=True)
    referrer = models.CharField(max_length=400, blank=True)
    visitor_hash = models.CharField(max_length=64, db_index=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # Set for sign-ins, and for a failed sign-in only when the username given
    # matches a real account. Kept as SET_NULL so deleting a staff member does
    # not take the history of what they did with them.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="visit_events",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["kind", "-created_at"])]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.label or self.path}"

    @staticmethod
    def make_visitor_hash(ip, user_agent, day):
        raw = f"{ip}|{user_agent}|{day.isoformat()}|fonanyi"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
