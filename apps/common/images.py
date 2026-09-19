"""Shrink uploaded photographs before they are stored.

Staff upload straight from a phone, so a single gallery image can be 5 MB.
Cloudflare caches whatever the origin serves and `next/image` optimisation is
off in a static export, so if we do not do this here, nobody does — and the
people worst affected are visitors on mobile data.
"""
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps

MAX_EDGE = 1600
QUALITY = 82


def compress(image_field, max_edge: int = MAX_EDGE, quality: int = QUALITY):
    """Return a re-encoded upload, or the original if it cannot be processed."""
    if not image_field or not getattr(image_field, "file", None):
        return image_field

    try:
        with Image.open(image_field.file) as opened:
            # Phone photos carry orientation in EXIF; bake it in before resizing.
            picture = ImageOps.exif_transpose(opened)
            has_alpha = picture.mode in ("RGBA", "LA", "P")
            picture = picture.convert("RGBA" if has_alpha else "RGB")
            picture.thumbnail((max_edge, max_edge), Image.LANCZOS)

            buffer = BytesIO()
            if has_alpha:
                picture.save(buffer, "PNG", optimize=True)
                extension, content_type = "png", "image/png"
            else:
                picture.save(
                    buffer, "JPEG", quality=quality, optimize=True, progressive=True
                )
                extension, content_type = "jpg", "image/jpeg"
    except Exception:
        # A file Pillow cannot read is a validation problem, not ours to mask.
        image_field.file.seek(0)
        return image_field

    stem = image_field.name.rsplit(".", 1)[0][:80]
    buffer.seek(0)
    return InMemoryUploadedFile(
        buffer,
        field_name=None,
        name=f"{stem}.{extension}",
        content_type=content_type,
        size=buffer.getbuffer().nbytes,
        charset=None,
    )


THUMB_EDGE = 600
THUMB_QUALITY = 74


def make_thumbnail(image_field, max_edge: int = THUMB_EDGE, quality: int = THUMB_QUALITY):
    """Return a small JPEG copy of an image, or None if it cannot be made.

    Grids render these at roughly 230-300px. Serving the full 1600px original
    into that slot costs a visitor on mobile data about ten times what it
    needs to, which is the whole reason this exists.
    """
    if not image_field:
        return None
    try:
        image_field.open()
        with Image.open(image_field) as opened:
            picture = ImageOps.exif_transpose(opened).convert("RGB")
            picture.thumbnail((max_edge, max_edge), Image.LANCZOS)
            buffer = BytesIO()
            picture.save(buffer, "JPEG", quality=quality, optimize=True, progressive=True)
    except Exception:
        return None

    stem = Path(image_field.name).stem[:80]
    buffer.seek(0)
    return ContentFile(buffer.getvalue(), name=f"{stem}-thumb.jpg")
