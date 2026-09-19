from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.siteinfo.models import ContentFlag

from ._rebuild import request_rebuild


class Command(BaseCommand):
    help = (
        "Rebuild the Cloudflare site only if content changed since the last "
        "rebuild. Run every 10 minutes from cron; it is a no-op most of the time."
    )

    def handle(self, *args, **options):
        flag = ContentFlag.load()
        if not flag.is_dirty:
            self.stdout.write("No content changes; nothing to do.")
            return
        if request_rebuild(self.stdout):
            flag.is_dirty = False
            flag.last_rebuild_at = timezone.now()
            flag.save(update_fields=["is_dirty", "last_rebuild_at", "updated_at"])
