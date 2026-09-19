from django.db import models

from apps.common.models import TimeStampedModel


class JobApplication(TimeStampedModel):
    """Someone asking to work with us, usually on the canopy crew."""

    ROLE_CHOICES = [
        ("canopy", "Canopy setup crew"),
        ("driver", "Driver"),
        ("solar", "Solar technician"),
        ("electrical", "Electrician"),
        ("boutique", "Boutique & sales"),
        ("other", "Something else"),
    ]
    AVAILABILITY_CHOICES = [
        ("weekends", "Weekends"),
        ("weekdays", "Weekdays"),
        ("full_time", "Full time"),
        ("on_call", "On call, event by event"),
    ]
    STATUS_CHOICES = [
        ("new", "New"),
        ("reviewing", "Reviewing"),
        ("shortlisted", "Shortlisted"),
        ("hired", "Hired"),
        ("declined", "Declined"),
        ("archived", "Archived"),
    ]

    full_name = models.CharField(max_length=140)
    phone = models.CharField(max_length=40)
    email = models.EmailField(blank=True)
    location = models.CharField(max_length=140, blank=True, help_text="Town or quarter.")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="canopy")
    availability = models.CharField(
        max_length=20, choices=AVAILABILITY_CHOICES, default="on_call"
    )
    years_experience = models.PositiveSmallIntegerField(default=0)
    about = models.TextField(help_text="What they have done before.")
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="new")
    source_ip = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "-created_at"])]

    def __str__(self):
        return f"{self.full_name} - {self.get_role_display()}"
