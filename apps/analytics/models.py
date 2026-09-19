import hashlib

from django.db import models


class VisitEvent(models.Model):
    """One page view or outbound/link click.

    No cookies and no raw IPs are stored: the visitor is identified by a
    salted daily hash, which is enough to count unique visitors without
    keeping personal data.
    """

    KIND_CHOICES = [("page", "Page view"), ("link", "Link click")]

    kind = models.CharField(max_length=8, choices=KIND_CHOICES, default="page")
    path = models.CharField(max_length=300, db_index=True)
    label = models.CharField(max_length=200, blank=True)
    referrer = models.CharField(max_length=400, blank=True)
    visitor_hash = models.CharField(max_length=64, db_index=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["kind", "-created_at"])]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.label or self.path}"

    @staticmethod
    def make_visitor_hash(ip, user_agent, day):
        raw = f"{ip}|{user_agent}|{day.isoformat()}|fonanyi"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
