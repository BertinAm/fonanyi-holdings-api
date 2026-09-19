from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.blog.models import Post

from ._rebuild import request_rebuild


class Command(BaseCommand):
    help = (
        "Publish posts whose scheduled time has passed, then rebuild the "
        "Cloudflare site. Run every 15 minutes from cron."
    )

    def handle(self, *args, **options):
        due = Post.objects.filter(is_published=False, scheduled_for__isnull=False,
                                  scheduled_for__lte=timezone.now())
        titles = list(due.values_list("title", flat=True))
        if not titles:
            self.stdout.write("Nothing scheduled.")
            return
        for post in due:
            post.is_published = True
            post.published_at = post.scheduled_for
            post.save()
        self.stdout.write(self.style.SUCCESS(f"Published: {', '.join(titles)}"))
        request_rebuild(self.stdout)
