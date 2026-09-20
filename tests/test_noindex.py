"""Nothing this domain serves should turn up in a search result.

A robots.txt cannot enforce it: the domain is proxied and Cloudflare serves
its own managed robots.txt, so only a response header survives.
"""
import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

NOINDEX = "noindex, nofollow, noarchive, nosnippet"


@pytest.fixture
def api():
    return APIClient()


@pytest.mark.parametrize(
    "url",
    [
        "/api/site-settings/",
        "/api/gallery/",
        "/api/posts/",
        "/api/testimonials/",
        "/django-admin/login/",
    ],
)
def test_every_response_is_noindexed(api, url):
    assert api.get(url).headers["X-Robots-Tag"] == NOINDEX


def test_a_404_is_noindexed_too(api):
    response = api.get("/api/nothing-here/")

    assert response.status_code == 404
    assert response.headers["X-Robots-Tag"] == NOINDEX


def test_an_unauthorised_admin_page_is_noindexed(api):
    response = api.get("/api/admin/messages/")

    assert response.status_code == 401
    assert response.headers["X-Robots-Tag"] == NOINDEX
