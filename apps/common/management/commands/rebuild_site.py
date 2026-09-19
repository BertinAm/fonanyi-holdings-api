from django.core.management.base import BaseCommand

from ._rebuild import request_rebuild


class Command(BaseCommand):
    help = "Manually trigger a Cloudflare Pages rebuild."

    def handle(self, *args, **options):
        request_rebuild(self.stdout)
