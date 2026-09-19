"""Load the starter content shipped with the project.

Idempotent: re-running it will not duplicate anything. Intended for a fresh
install so the site has real photos and copy before the client takes over.
"""
from pathlib import Path

from django.conf import settings
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

# settings.py lives at backend/config/, so BASE_DIR is backend/.
DEFAULT_PHOTOS_DIR = Path(settings.BASE_DIR) / "seed_media" / "photos"
DEFAULT_BOUTIQUE_DIR = Path(settings.BASE_DIR) / "seed_media" / "boutique"
POST_COVER = "IMG-20260917-WA0071.jpg"
WELCOME_POST_COVER_NAME = "two-trades-under-one-roof.jpg"

# Too soft, too dark, or too much glass glare and storage to show at size.
BOUTIQUE_HOLDBACK = {
    "beadwork-and-shoes",
    "dress-rails",
    "handbag-cases",
    "jewellery-case",
    "shopfront-wide",
    "wigs-corner",
    "wigs-stands",
}

BOUTIQUE_TITLES = {
    "shopfront-mannequins": "Shopfront window",
    "shopfront-wide": "The boutique from the street",
    "interior-wigs-textiles": "Wigs and textiles",
    "interior-rails-jewellery": "Rails and jewellery case",
    "jewellery-case": "Jewellery and clutches",
    "handbag-cases": "Handbags",
    "dress-rails": "Dress rails",
    "beadwork-and-shoes": "Beadwork and footwear",
    "wigs-display": "Wigs on display",
    "wigs-corner": "Wig corner",
    "wigs-stands": "Wigs on stands",
}

BOUTIQUE_ALT = {
    "shopfront-mannequins": "The boutique window, with mannequins in embroidered African wear and a men's senator suit",
    "shopfront-wide": "The full shopfront, its window displaying beaded gowns and a sequinned top",
    "interior-wigs-textiles": "Inside the boutique: wigs, bagged textiles and rails of printed dresses",
    "interior-rails-jewellery": "Rails of covered garments beside a glass case of jewellery",
    "jewellery-case": "A display case of necklaces, earrings and beaded evening clutches",
    "handbag-cases": "Glass cabinets of handbags in assorted leathers and colours",
    "dress-rails": "Long rails of dresses hanging in protective covers",
    "beadwork-and-shoes": "Traditional beaded necklaces on display next to a shelf of women's shoes",
    "wigs-display": "Wigs styled on stands, from short crops to long waves",
    "wigs-corner": "A corner shelf of wigs in several lengths and colours",
    "wigs-stands": "Wigs on tripod stands in the middle of the shop floor",
}

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
        photos_dir = (
            Path(options["photos"]).expanduser() if options["photos"] else DEFAULT_PHOTOS_DIR
        )
        self._seed_settings()
        self._seed_testimonials()
        self._seed_post(photos_dir)
        if options["photos"]:
            self._seed_photos(photos_dir)
        # The boutique photographs ship with the repository, so they import
        # whether or not --photos was given. They are what makes the gallery's
        # Fashion filter show anything.
        self._seed_photos(
            DEFAULT_BOUTIQUE_DIR,
            category="fashion",
            alt="The Fonanyi boutique in Buea",
            start_order=100,
        )
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
        # get_or_create keys on name, so these are only absent once the team
        # has replaced them with real quotes -- at which point re-running the
        # seed would put every placeholder back on the live homepage. Seed
        # only into an empty table.
        if Testimonial.objects.exists():
            self.stdout.write("Testimonials: already present, left alone.")
            return

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

    def _seed_post(self, photos_dir):
        if Post.objects.filter(title=WELCOME_POST["title"]).exists():
            return
        post = Post(**WELCOME_POST, is_published=True, published_at=timezone.now())

        # A card with no cover falls back to a plain gradient, so give the
        # first article one of the company's own photographs. It doubles as
        # the OG image when the article is shared.
        cover = photos_dir / POST_COVER
        if cover.is_file():
            with cover.open("rb") as fh:
                post.cover_image.save(f"{WELCOME_POST_COVER_NAME}", File(fh), save=False)
        else:
            self.stderr.write(f"{cover} not found; article published without a cover.")

        post.save()
        self.stdout.write("First article published.")

    def _seed_photos(self, directory, category="events", alt="Fonanyi event setup in Buea",
                     start_order=0):
        if not directory.is_dir():
            self.stderr.write(f"{directory} is not a directory; skipping photos.")
            return
        files = sorted(
            p for p in directory.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )
        created = 0
        for order, path in enumerate(files):
            # Dedupe on the title actually stored, not on the file stem.
            # Those differ for the boutique set, and keying on the stem would
            # make every re-run import the whole folder again.
            title = BOUTIQUE_TITLES.get(path.stem, path.stem)
            if GalleryImage.objects.filter(title=title).exists():
                continue
            image = GalleryImage(
                title=title,
                category=category,
                alt_text=BOUTIQUE_ALT.get(path.stem, alt),
                sort_order=start_order + order,
                # The first set from the shop varied a lot. The weaker frames
                # are imported but left unpublished, so the team can see them
                # in the dashboard and decide, without them going live.
                is_published=path.stem not in BOUTIQUE_HOLDBACK,
            )
            with path.open("rb") as fh:
                image.image.save(path.name, File(fh), save=True)
            created += 1
        self.stdout.write(f"Gallery: {created} photos imported from {directory}.")
