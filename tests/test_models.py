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
