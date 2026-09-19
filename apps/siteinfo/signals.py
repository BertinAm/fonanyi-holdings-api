"""Flag the site as needing a rebuild whenever public content changes."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.blog.models import Post
from apps.gallery.models import GalleryImage

from .models import ContentFlag, SiteSettings, Testimonial

WATCHED = (Post, GalleryImage, Testimonial, SiteSettings)


@receiver(post_save)
@receiver(post_delete)
def flag_content_change(sender, **kwargs):
    if sender in WATCHED:
        ContentFlag.mark_dirty()
