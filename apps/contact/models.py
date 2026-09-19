from django.db import models

from apps.common.models import TimeStampedModel


class ContactMessage(TimeStampedModel):
    DIVISION_CHOICES = [
        ("energy", "Energy & Rentals"),
        ("fashion", "Fashion & Textiles"),
        ("other", "Something else"),
    ]
    STATUS_CHOICES = [
        ("new", "New"),
        ("read", "Read"),
        ("replied", "Replied"),
        ("archived", "Archived"),
    ]

    full_name = models.CharField(max_length=140)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    division = models.CharField(max_length=20, choices=DIVISION_CHOICES, default="other")
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="new")
    # Kept for abuse triage only, never exposed on the public API.
    source_ip = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.full_name} - {self.subject or self.get_division_display()}"
