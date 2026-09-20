"""Put media files back under MEDIA_ROOT for rows that already exist.

The database survived the rebuild of the hosting account; the uploaded files
did not, because they lived outside the checkout. Every original came from
seed_media/, which is in the repository, so the rows can be re-attached to
their bytes without touching the rows themselves.

This deliberately does not re-seed. It reads the path each row already stores
and writes that exact path, so titles, captions, ordering and publication
state are left alone. Anything already on disk is skipped, which makes it safe
to run on every deploy.

    python manage.py restore_media --check     # report only
    python manage.py restore_media             # copy the missing files
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from apps.blog.models import Post
from apps.common.images import make_thumbnail
from apps.gallery.models import GalleryImage
from apps.siteinfo.models import Testimonial

# Django appends a random suffix when a name is taken: foo_a1B2c3D.jpg.
DEDUPE_SUFFIX = re.compile(r"_[A-Za-z0-9]{7}$")

# The first article's cover was saved under a readable name rather than the
# camera's, so its stem cannot find its own source file.
RENAMED = {"two-trades-under-one-roof": "IMG-20260917-WA0071"}

# Fields whose bytes come straight from seed_media/.
ORIGINALS = [
    (GalleryImage, "image", "gallery image"),
    (Post, "cover_image", "article cover"),
    (Testimonial, "avatar", "testimonial avatar"),
]

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


class Command(BaseCommand):
    help = "Re-attach media files from seed_media/ to rows whose files are missing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Report what is missing without writing anything.",
        )
        parser.add_argument(
            "--source",
            default=str(Path(settings.BASE_DIR) / "seed_media"),
            help="Directory holding the original files (default: seed_media/).",
        )

    def handle(self, *args, **options):
        self.source_dir = Path(options["source"])
        self.media_root = Path(settings.MEDIA_ROOT)
        self.dry_run = options["check"]

        self.stdout.write(f"MEDIA_ROOT : {self.media_root}")
        self.stdout.write(f"source     : {self.source_dir}")

        if not self.source_dir.is_dir():
            self.stderr.write(f"{self.source_dir} is not a directory; nothing to restore from.")
            return

        # basename -> path and stem -> path, so a stored name resolves whether
        # or not it carries a dedupe suffix or a different extension.
        self.by_name: dict[str, Path] = {}
        self.by_stem: dict[str, Path] = {}
        for path in sorted(self.source_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
                self.by_name.setdefault(path.name, path)
                self.by_stem.setdefault(path.stem, path)
        self.stdout.write(f"available  : {len(self.by_name)} source files")

        present, missing, restored, unmatched = self._restore_originals()
        # Thumbnails are derived, not stored anywhere, so they are rebuilt from
        # the full image once that is back in place.
        thumbs_present, thumbs_missing, thumbs_made, thumbs_failed = self._rebuild_thumbnails()

        verb = "would be restored" if self.dry_run else "restored"
        made = "would be rebuilt" if self.dry_run else "rebuilt"
        self.stdout.write(
            f"\nOriginals : {present} on disk, {missing} missing, {restored} {verb}, "
            f"{unmatched} with no matching source."
            f"\nThumbnails: {thumbs_present} on disk, {thumbs_missing} missing, "
            f"{thumbs_made} {made}, {thumbs_failed} could not be made."
        )
        if unmatched:
            self.stderr.write("Some rows have no source file. Re-upload those in the dashboard.")

    def _restore_originals(self):
        present = missing = restored = unmatched = 0

        for model, field, label in ORIGINALS:
            rows = model.objects.exclude(**{field: ""}).exclude(**{f"{field}__isnull": True})
            for row in rows.iterator():
                stored = getattr(row, field).name
                if not stored:
                    continue
                if self._on_disk(stored):
                    present += 1
                    continue

                missing += 1
                origin = self._find(Path(stored).name)
                if origin is None:
                    unmatched += 1
                    self.stderr.write(f"  no source for {label}: {stored}")
                    continue

                if self.dry_run:
                    self.stdout.write(f"  would restore {stored}  <-  {origin.name}")
                    continue

                # Copied byte for byte. Every file in seed_media/ is already
                # within the 1600px cap that uploads are compressed to, so
                # re-encoding here would only cost quality.
                destination = self.media_root / stored
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(origin, destination)
                restored += 1

        return present, missing, restored, unmatched

    def _rebuild_thumbnails(self):
        present = missing = made = failed = 0

        rows = GalleryImage.objects.exclude(thumbnail="").exclude(thumbnail__isnull=True)
        for row in rows.iterator():
            stored = row.thumbnail.name
            if not stored:
                continue
            if self._on_disk(stored):
                present += 1
                continue

            missing += 1
            full = self.media_root / row.image.name if row.image else None
            if full is None or not full.is_file():
                failed += 1
                self.stderr.write(f"  cannot rebuild {stored}: full image is missing too")
                continue

            if self.dry_run:
                self.stdout.write(f"  would rebuild {stored}  <-  {row.image.name}")
                continue

            with full.open("rb") as handle:
                thumb = make_thumbnail(File(handle, name=full.name))
            if thumb is None:
                failed += 1
                self.stderr.write(f"  Pillow could not read {row.image.name}")
                continue

            destination = self.media_root / stored
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(thumb.read())
            made += 1

        return present, missing, made, failed

    def _on_disk(self, stored: str) -> bool:
        path = self.media_root / stored
        return path.is_file() and path.stat().st_size > 0

    def _find(self, name: str) -> Path | None:
        if name in self.by_name:
            return self.by_name[name]
        stem = Path(name).stem
        for candidate in (stem, DEDUPE_SUFFIX.sub("", stem)):
            candidate = RENAMED.get(candidate, candidate)
            if candidate in self.by_stem:
                return self.by_stem[candidate]
        return None
