"""The public API must never leak unpublished content or accept writes."""
import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.blog.models import Post
from apps.gallery.models import GalleryImage
from apps.siteinfo.models import Testimonial

pytestmark = pytest.mark.django_db


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def staff():
    return User.objects.create_user("staff", password="pw", is_staff=True)


@pytest.fixture
def civilian():
    return User.objects.create_user("civilian", password="pw")


def auth(api, user):
    from rest_framework_simplejwt.tokens import RefreshToken

    token = RefreshToken.for_user(user).access_token
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api


def test_drafts_are_invisible_to_the_public(api):
    Post.objects.create(title="Draft", body="x", is_published=False)
    Post.objects.create(title="Live", body="x", is_published=True, published_at=timezone.now())

    response = api.get("/api/posts/")

    assert response.status_code == 200
    assert [p["title"] for p in response.json()["results"]] == ["Live"]


def test_draft_detail_is_404_for_the_public(api):
    post = Post.objects.create(title="Draft", body="x", is_published=False)

    assert api.get(f"/api/posts/{post.slug}/").status_code == 404


def test_staff_see_drafts(api, staff):
    Post.objects.create(title="Draft", body="x", is_published=False)

    response = auth(api, staff).get("/api/posts/")

    assert [p["title"] for p in response.json()["results"]] == ["Draft"]


def test_unpublished_gallery_images_are_hidden(api):
    GalleryImage.objects.create(title="Hidden", image="x.jpg", is_published=False)
    GalleryImage.objects.create(title="Shown", image="y.jpg", is_published=True)

    titles = [g["title"] for g in api.get("/api/gallery/").json()["results"]]

    assert titles == ["Shown"]


def test_unfeatured_testimonials_are_hidden(api):
    Testimonial.objects.create(name="Hidden", quote="q", is_featured=False)
    Testimonial.objects.create(name="Shown", quote="q", is_featured=True)

    names = [t["name"] for t in api.get("/api/testimonials/").json()["results"]]

    assert names == ["Shown"]


@pytest.mark.parametrize(
    "path",
    ["/api/posts/", "/api/gallery/", "/api/testimonials/"],
)
def test_anonymous_writes_are_rejected(api, path):
    assert api.post(path, {}, format="json").status_code in (401, 403)


@pytest.mark.parametrize(
    "path",
    ["/api/posts/", "/api/gallery/", "/api/testimonials/", "/api/site-settings/"],
)
def test_non_staff_writes_are_rejected(api, civilian, path):
    response = auth(api, civilian).post(path, {}, format="json")

    assert response.status_code in (403, 405)


def test_non_staff_cannot_read_enquiries(api, civilian):
    assert auth(api, civilian).get("/api/admin/messages/").status_code == 403


def test_non_staff_cannot_read_the_dashboard_summary(api, civilian):
    assert auth(api, civilian).get("/api/admin/summary/").status_code == 403


def test_non_staff_cannot_sign_in_to_the_dashboard(api, civilian):
    response = api.post(
        "/api/auth/login/", {"username": "civilian", "password": "pw"}, format="json"
    )

    assert response.status_code == 400
    assert "dashboard" in str(response.json()).lower()


def test_staff_can_sign_in(api, staff):
    response = api.post("/api/auth/login/", {"username": "staff", "password": "pw"}, format="json")

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["username"] == "staff"
    assert body["access"] and body["refresh"]
