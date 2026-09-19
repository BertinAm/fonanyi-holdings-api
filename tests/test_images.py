"""Uploads must be shrunk before they reach disk."""
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.gallery.models import GalleryImage
from apps.siteinfo.models import Testimonial

pytestmark = pytest.mark.django_db


def big_jpeg(width=4000, height=3000):
    buffer = BytesIO()
    # Noise rather than flat colour, so the file cannot compress to nothing.
    picture = Image.effect_noise((width, height), 60).convert("RGB")
    picture.save(buffer, "JPEG", quality=95)
    buffer.seek(0)
    return SimpleUploadedFile("phone-photo.jpg", buffer.read(), "image/jpeg")


def test_a_large_upload_is_resized_and_shrunk(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    upload = big_jpeg()
    original_size = upload.size

    item = GalleryImage.objects.create(title="Big", image=upload)

    with Image.open(item.image.path) as stored:
        assert max(stored.size) == 1600
    assert item.image.size < original_size


def test_avatars_are_capped_smaller(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path

    item = Testimonial.objects.create(name="A", quote="q", avatar=big_jpeg())

    with Image.open(item.avatar.path) as stored:
        assert max(stored.size) == 400


def test_resaving_does_not_recompress(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    item = GalleryImage.objects.create(title="Big", image=big_jpeg())
    first_size = item.image.size

    item.title = "Renamed"
    item.save()

    assert item.image.size == first_size


def test_a_small_image_is_not_enlarged(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path

    item = GalleryImage.objects.create(title="Small", image=big_jpeg(300, 200))

    with Image.open(item.image.path) as stored:
        assert stored.size == (300, 200)


def test_a_thumbnail_is_generated_on_upload(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path

    item = GalleryImage.objects.create(title="Big", image=big_jpeg())

    assert item.thumbnail
    with Image.open(item.thumbnail.path) as thumb:
        assert max(thumb.size) == 600
    assert item.thumbnail.size < item.image.size


def test_the_api_serves_the_thumbnail_for_grids(tmp_path, settings, client):
    settings.MEDIA_ROOT = tmp_path
    GalleryImage.objects.create(title="Big", image=big_jpeg())

    row = client.get("/api/gallery/").json()["results"][0]

    assert row["thumb_url"] and row["thumb_url"] != row["image_url"]
    assert "-thumb" in row["thumb_url"]


def test_resaving_does_not_regenerate_the_thumbnail(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    item = GalleryImage.objects.create(title="Big", image=big_jpeg())
    first = item.thumbnail.name

    item.title = "Renamed"
    item.save()

    assert item.thumbnail.name == first
