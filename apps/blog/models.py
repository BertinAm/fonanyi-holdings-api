from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.common.images import compress
from apps.common.models import TimeStampedModel


class Post(TimeStampedModel):
    DIVISION_CHOICES = [
        ("energy", "Energy & Rentals"),
        ("fashion", "Fashion & Textiles"),
        ("company", "Company News"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    excerpt = models.TextField(max_length=400, blank=True)
    body = models.TextField(help_text="Markdown is rendered by the frontend.")
    cover_image = models.ImageField(upload_to="blog/%Y/%m/", blank=True, null=True)
    division = models.CharField(max_length=20, choices=DIVISION_CHOICES, default="company")
    author_name = models.CharField(max_length=120, default="Fonanyi Holdings")
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)
    scheduled_for = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Leave unpublished and set a time; the publish_scheduled cron job goes live for you.",
    )
    read_minutes = models.PositiveSmallIntegerField(default=3)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        indexes = [models.Index(fields=["is_published", "published_at"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.cover_image and not self.cover_image._committed and hasattr(self.cover_image, "file"):
            self.cover_image = compress(self.cover_image)
        if not self.slug:
            base = slugify(self.title)[:200] or "post"
            slug, n = base, 2
            while Post.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        if self.is_published and self.published_at is None:
            self.published_at = timezone.now()
        # Roughly 200 words a minute, so the card can show a read time.
        words = len(self.body.split())
        self.read_minutes = max(1, round(words / 200))
        return super().save(*args, **kwargs)
