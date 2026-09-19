from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class SiteSettings(TimeStampedModel):
    """Single row holding the contact details shown across the site."""

    company_name = models.CharField(max_length=120, default="Fonanyi Holdings Ltd")
    tagline = models.CharField(max_length=200, blank=True)
    street = models.CharField(max_length=160, default="Chief Street, Bomaka")
    city = models.CharField(max_length=120, default="Buea, Southwest Region")
    country = models.CharField(max_length=80, default="Cameroon")
    phone_primary = models.CharField(max_length=40, blank=True)
    phone_secondary = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    hours_weekday = models.CharField(max_length=80, default="8am - 6pm")
    hours_saturday = models.CharField(max_length=80, default="8am - 4pm")
    hours_sunday = models.CharField(max_length=80, default="Closed")
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    # Homepage counters, editable from the dashboard rather than hard-coded.
    stat_events_covered = models.PositiveIntegerField(default=0)
    stat_solar_installs = models.PositiveIntegerField(default=0)
    stat_workers = models.PositiveIntegerField(default=0)
    stat_countries_sourced = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError("Only one SiteSettings row may exist.")
        return super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj


class Testimonial(TimeStampedModel):
    DIVISION_CHOICES = [
        ("energy", "Energy & Rentals"),
        ("fashion", "Fashion & Textiles"),
        ("general", "General"),
    ]

    name = models.CharField(max_length=120)
    role_business = models.CharField(max_length=160, blank=True)
    quote = models.TextField()
    division = models.CharField(max_length=20, choices=DIVISION_CHOICES, default="general")
    rating = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    avatar = models.ImageField(upload_to="testimonials/", blank=True, null=True)
    is_featured = models.BooleanField(default=True, help_text="Show on the homepage.")
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_division_display()})"


class ContentFlag(TimeStampedModel):
    """Marks that published content changed since the last Cloudflare rebuild.

    A cron job checks this every few minutes instead of us firing an outbound
    HTTPS call inside a Passenger worker, which shared hosting handles badly.
    """

    is_dirty = models.BooleanField(default=False)
    last_rebuild_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Rebuild flag"
        verbose_name_plural = "Rebuild flag"

    def __str__(self):
        return "content changed" if self.is_dirty else "up to date"

    @classmethod
    def load(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj

    @classmethod
    def mark_dirty(cls):
        if cls.objects.update(is_dirty=True) == 0:
            cls.objects.create(is_dirty=True)
