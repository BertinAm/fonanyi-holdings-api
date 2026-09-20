"""Rows whose files were lost must be re-attachable from seed_media/.

The hosting account was rebuilt with the database intact but MEDIA_ROOT gone.
restore_media exists for that, and it runs on every deploy, so it also has to
be a no-op once the files are back.
"""
from io import BytesIO
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image

from apps.gallery.models import GalleryImage

pytestmark = pytest.mark.django_db


def photo(name):
    buffer = BytesIO()
    Image.effect_noise((900, 700), 60).convert("RGB").save(buffer, "JPEG", quality=90)
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), "image/jpeg")


@pytest.fixture
def source_dir(tmp_path):
    directory = tmp_path / "seed_media"
    directory.mkdir()
    return directory


def make_row(source_dir, stem="event-one"):
    """A gallery row whose original also exists in the source directory."""
    upload = photo(f"{stem}.jpg")
    (source_dir / f"{stem}.jpg").write_bytes(upload.read())
    upload.seek(0)
    return GalleryImage.objects.create(title=stem, image=upload)


def test_missing_files_are_restored_without_touching_the_rows(tmp_path, settings, source_dir):
    settings.MEDIA_ROOT = tmp_path / "media"
    row = make_row(source_dir)
    image_name, thumb_name = row.image.name, row.thumbnail.name
    assert thumb_name, "the model should have generated a thumbnail on save"

    for path in Path(settings.MEDIA_ROOT).rglob("*"):
        if path.is_file():
            path.unlink()

    call_command("restore_media", source=str(source_dir))

    row.refresh_from_db()
    assert row.image.name == image_name
    assert row.thumbnail.name == thumb_name
    assert (Path(settings.MEDIA_ROOT) / image_name).stat().st_size > 0
    assert (Path(settings.MEDIA_ROOT) / thumb_name).stat().st_size > 0


def test_a_rebuilt_thumbnail_is_smaller_than_the_full_image(tmp_path, settings, source_dir):
    settings.MEDIA_ROOT = tmp_path / "media"
    row = make_row(source_dir)
    (Path(settings.MEDIA_ROOT) / row.thumbnail.name).unlink()

    call_command("restore_media", source=str(source_dir))

    full = (Path(settings.MEDIA_ROOT) / row.image.name).stat().st_size
    thumb = (Path(settings.MEDIA_ROOT) / row.thumbnail.name).stat().st_size
    assert 0 < thumb < full


def test_running_twice_changes_nothing(tmp_path, settings, source_dir):
    settings.MEDIA_ROOT = tmp_path / "media"
    row = make_row(source_dir)
    for path in Path(settings.MEDIA_ROOT).rglob("*"):
        if path.is_file():
            path.unlink()

    call_command("restore_media", source=str(source_dir))
    fingerprint = {
        p: (p.stat().st_size, p.stat().st_mtime_ns)
        for p in Path(settings.MEDIA_ROOT).rglob("*")
        if p.is_file()
    }
    assert fingerprint

    call_command("restore_media", source=str(source_dir))

    again = {
        p: (p.stat().st_size, p.stat().st_mtime_ns)
        for p in Path(settings.MEDIA_ROOT).rglob("*")
        if p.is_file()
    }
    assert again == fingerprint


def test_check_reports_without_writing(tmp_path, settings, source_dir, capsys):
    settings.MEDIA_ROOT = tmp_path / "media"
    row = make_row(source_dir)
    (Path(settings.MEDIA_ROOT) / row.image.name).unlink()

    call_command("restore_media", "--check", source=str(source_dir))

    assert not (Path(settings.MEDIA_ROOT) / row.image.name).exists()
    assert "would restore" in capsys.readouterr().out


def test_a_row_with_no_source_is_reported_not_crashed(tmp_path, settings, source_dir, capsys):
    settings.MEDIA_ROOT = tmp_path / "media"
    row = make_row(source_dir)
    (source_dir / Path(row.image.name).name).unlink()
    (Path(settings.MEDIA_ROOT) / row.image.name).unlink()

    call_command("restore_media", source=str(source_dir))

    assert "no matching source" in capsys.readouterr().out
