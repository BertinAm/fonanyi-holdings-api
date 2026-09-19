"""Load the starter content shipped with the project.

Idempotent: re-running it will not duplicate anything. Intended for a fresh
install so the site has real photos and copy before the client takes over.
"""
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.blog.models import Post
from apps.gallery.models import GalleryImage
from apps.siteinfo.models import SiteSettings, Testimonial

TESTIMONIALS = [
    (
        "Ngozi Ashu",
        "Ashu Events, Buea",
        "energy",
        "Fonanyi set up canopies for our wedding reception and everything was ready hours "
        "ahead of time. Clean tents, no stress.",
    ),
    (
        "Divine Tabe",
        "Tabe Construction Ltd",
        "energy",
        "They installed solar for our site office. Straightforward quote, honest timeline, "
        "and it has worked without issue since.",
    ),
    (
        "Clarisse Mbah",
        "Mbah Boutique, Douala",
        "fashion",
        "The fashion team delivered our order on time and the quality was better than I "
        "expected for the price.",
    ),
    (
        "Emmanuel Fru",
        "Fru Logistics, Limbe",
        "general",
        "Reliable truck support for our deliveries. Fair pricing and good communication "
        "from start to finish.",
    ),
]

WELCOME_POST = {
    "title": "Fonanyi Holdings brings two trades under one roof",
    "division": "company",
    "excerpt": (
        "A fashion house trading since 2010 and an energy and rentals division launched in "
        "2018 now operate as one company, registered in Buea."
    ),
    "body": (
        "Fonanyi Holdings Ltd was formed in Buea in 2025 to bring two established trades "
        "under one family roof.\n\n"
        "The fashion side has been trading since 2010, when it started out of a single "
        "shipping container. More than a decade of buying trips to Nigeria, Ghana, Togo and "
        "Benin grew it into the boutique it is today, stocking wears and textiles, footwear "
        "and bags, watches, and beauty care.\n\n"
        "The energy and rentals side launched in 2018 with its first canopies and chairs. It "
        "now runs a dedicated warehouse, a cargo truck and two K-trucks, and handles solar "
        "design and installation alongside event rentals and logistics.\n\n"
        "Bringing both under one company means one point of contact, one standard of work, "
        "and one crew accountable from the first call to the handover."
    ),
}


class Command(BaseCommand):
    help = "Seed site settings, testimonials, gallery photos and a first article."

    def add_arguments(self, parser):
        parser.add_argument(
            "--photos",
            default="",
            help="Directory of images to import into the gallery.",
        )

    def handle(self, *args, **options):
        self._seed_settings()
        self._seed_testimonials()
        self._seed_post()
        if options["photos"]:
            self._seed_photos(Path(options["photos"]).expanduser())
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    def _seed_settings(self):
        settings_row = SiteSettings.load()
        if not settings_row.tagline:
            settings_row.tagline = "Power, events, and style, all in one place."
            settings_row.stat_events_covered = 24
            settings_row.stat_solar_installs = 15
            settings_row.stat_workers = 20
            settings_row.stat_countries_sourced = 4
            settings_row.save()
            self.stdout.write("Site settings initialised.")

    def _seed_testimonials(self):
        created = 0
        for order, (name, role, division, quote) in enumerate(TESTIMONIALS):
            _, made = Testimonial.objects.get_or_create(
                name=name,
                defaults={
                    "role_business": role,
                    "division": division,
                    "quote": quote,
                    "sort_order": order,
                },
            )
            created += int(made)
        self.stdout.write(f"Testimonials: {created} added.")

    def _seed_post(self):
        if Post.objects.filter(title=WELCOME_POST["title"]).exists():
            return
        Post.objects.create(
            **WELCOME_POST, is_published=True, published_at=timezone.now()
        )
        self.stdout.write("First article published.")

    def _seed_photos(self, directory):
        if not directory.is_dir():
            self.stderr.write(f"{directory} is not a directory; skipping photos.")
            return
        files = sorted(
            p for p in directory.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )
        created = 0
        for order, path in enumerate(files):
            if GalleryImage.objects.filter(title=path.stem).exists():
                continue
            image = GalleryImage(
                title=path.stem,
                category="events",
                alt_text="Fonanyi event setup in Buea",
                sort_order=order,
            )
            with path.open("rb") as fh:
                image.image.save(path.name, File(fh), save=True)
            created += 1
        self.stdout.write(f"Gallery: {created} photos imported from {directory}.")
