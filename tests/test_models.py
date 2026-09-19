import os
import pytest
from django.utils import timezone

from apps.analytics.models import VisitEvent
from apps.blog.models import Post
from apps.siteinfo.models import ContentFlag, SiteSettings

pytestmark = pytest.mark.django_db


def test_slugs_are_derived_and_made_unique():
    first = Post.objects.create(title="Solar in Buea", body="x")
    second = Post.objects.create(title="Solar in Buea", body="x")

    assert first.slug == "solar-in-buea"
    assert second.slug == "solar-in-buea-2"


def test_publishing_stamps_the_time():
    post = Post.objects.create(title="Live", body="x", is_published=True)

    assert post.published_at is not None


def test_read_time_comes_from_the_body():
    post = Post.objects.create(title="Long", body=" ".join(["word"] * 600))

    assert post.read_minutes == 3


def test_only_one_settings_row_can_exist():
    from django.core.exceptions import ValidationError

    SiteSettings.load()
    with pytest.raises(ValidationError):
        SiteSettings.objects.create()


def test_saving_content_flags_the_site_for_rebuild():
    ContentFlag.objects.all().update(is_dirty=False)

    Post.objects.create(title="Something new", body="x")

    assert ContentFlag.load().is_dirty is True


def test_visitor_hashes_differ_by_day():
    today = timezone.now().date()
    tomorrow = today + timezone.timedelta(days=1)

    a = VisitEvent.make_visitor_hash("1.2.3.4", "UA", today)
    b = VisitEvent.make_visitor_hash("1.2.3.4", "UA", tomorrow)

    assert a != b
    assert a == VisitEvent.make_visitor_hash("1.2.3.4", "UA", today)


def test_visitor_hash_does_not_contain_the_address():
    digest = VisitEvent.make_visitor_hash("196.1.2.3", "UA", timezone.now().date())

    assert "196.1.2.3" not in digest
    assert len(digest) == 64


def test_seeding_leaves_existing_testimonials_alone():
    """Re-running the seed must not put placeholders back on a live site.

    get_or_create keys on the name, so once the team has swapped the seeded
    quotes for real ones the placeholders look absent and would be recreated.
    """
    from django.core.management import call_command

    from apps.siteinfo.models import Testimonial

    Testimonial.objects.create(name="Real Client", quote="A real quote.", division="rentals")

    call_command("seed_content")

    assert [t.name for t in Testimonial.objects.all()] == ["Real Client"]


def test_production_refuses_the_public_development_secret_key():
    """The fallback key is a literal in a public repo, so it must not boot.

    Django signs session cookies and password-reset tokens with SECRET_KEY.
    Falling back silently in production would let anyone who can read the
    repository forge both.
    """
    import importlib

    from django.core.exceptions import ImproperlyConfigured

    import config.settings as settings_module

    source = importlib.util.find_spec("config.settings").loader.get_source("config.settings")
    namespace = {"__name__": "config.settings_probe", "__file__": settings_module.__file__}
    os.environ["DJANGO_DEBUG"] = "False"
    os.environ["DJANGO_SECRET_KEY"] = "dev-only-insecure-key-change-me"
    try:
        with pytest.raises(ImproperlyConfigured, match="DJANGO_SECRET_KEY"):
            exec(compile(source, settings_module.__file__, "exec"), namespace)
    finally:
        os.environ.pop("DJANGO_DEBUG", None)
        os.environ.pop("DJANGO_SECRET_KEY", None)


def test_seeding_the_boutique_photos_twice_does_not_duplicate_them():
    """The stored title differs from the file stem, so dedupe must use the title.

    Keying the existence check on the file stem would make every re-run import
    the whole folder again.
    """
    from django.core.management import call_command

    from apps.gallery.models import GalleryImage

    call_command("seed_content")
    first = GalleryImage.objects.filter(category="fashion").count()

    call_command("seed_content")

    assert GalleryImage.objects.filter(category="fashion").count() == first
    assert first > 0
