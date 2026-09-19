import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.analytics.models import VisitEvent


class Command(BaseCommand):
    help = "Delete visit events older than ANALYTICS_RETENTION_DAYS. Run weekly from cron."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=None)

    def handle(self, *args, **options):
        days = options["days"] or int(os.environ.get("ANALYTICS_RETENTION_DAYS", 180))
        cutoff = timezone.now() - timedelta(days=days)
        # Delete in batches: shared hosting kills long-running queries.
        total = 0
        while True:
            ids = list(
                VisitEvent.objects.filter(created_at__lt=cutoff).values_list("id", flat=True)[:2000]
            )
            if not ids:
                break
            deleted, _ = VisitEvent.objects.filter(id__in=ids).delete()
            total += deleted
        self.stdout.write(self.style.SUCCESS(f"Pruned {total} events older than {days} days."))
