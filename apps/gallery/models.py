from django.db import models

from apps.common.images import compress
from apps.common.models import TimeStampedModel


class GalleryImage(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("events", "Events & Rentals"),
        ("energy", "Solar & Power"),
        ("fashion", "Fashion & Textiles"),
        ("logistics", "Logistics & Transport"),
    ]

    title = models.CharField(max_length=160, blank=True)
    caption = models.CharField(max_length=300, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="events")
    image = models.ImageField(upload_to="gallery/%Y/%m/")
    alt_text = models.CharField(max_length=200, blank=True)
    is_published = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        indexes = [models.Index(fields=["category", "is_published"])]

    def __str__(self):
        return self.title or f"{self.get_category_display()} #{self.pk}"

    def save(self, *args, **kwargs):
        if self.image and not self.image._committed and hasattr(self.image, "file"):
            self.image = compress(self.image)
        return super().save(*args, **kwargs)
