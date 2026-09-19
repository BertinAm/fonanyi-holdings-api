import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

PASSWORD = "not-the-real-one"


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def staff():
    return get_user_model().objects.create_user(
        username="manager", password=PASSWORD, is_staff=True
    )


def login(api, key=None, username="manager", password=PASSWORD):
    headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
    return api.post(
        "/api/auth/login/",
        {"username": username, "password": password},
        format="json",
        **headers,
    )


def test_a_login_without_a_key_is_not_replayed(api, staff):
    first = login(api)
    second = login(api)

    assert first.status_code == second.status_code == 200
    # Two genuine logins, so two distinct tokens.
    assert first.data["access"] != second.data["access"]
    assert "Idempotent-Replay" not in second


def test_a_retry_with_the_same_key_replays_the_first_response(api, staff):
    first = login(api, key="retry-1")
    second = login(api, key="retry-1")

    assert first.status_code == second.status_code == 200
    assert second.data["access"] == first.data["access"]
    assert second.data["refresh"] == first.data["refresh"]
    assert second["Idempotent-Replay"] == "true"


def test_a_different_key_issues_a_fresh_token(api, staff):
    first = login(api, key="retry-1")
    second = login(api, key="retry-2")

    assert first.data["access"] != second.data["access"]


def test_a_key_cannot_be_reused_for_different_credentials(api, staff):
    """The security property: a key is bound to the body that produced it.

    Someone who learns another person's Idempotency-Key must not be able to
    present it with their own (or no) password and be handed that person's
    token.
    """
    get_user_model().objects.create_user(
        username="other", password="different-one", is_staff=True
    )
    first = login(api, key="shared-key")
    assert first.status_code == 200

    stolen = login(api, key="shared-key", username="other", password="different-one")

    assert stolen.status_code == 200
    assert stolen.data["access"] != first.data["access"]
    assert "Idempotent-Replay" not in stolen


def test_a_failed_login_is_not_cached(api, staff):
    """A wrong password must not pin an error in place for the whole window."""
    bad = login(api, key="same-key", password="wrong")
    assert bad.status_code == 401

    good = login(api, key="same-key")

    assert good.status_code == 200
    assert "Idempotent-Replay" not in good


def test_an_overlong_key_is_ignored_rather_than_stored(api, staff):
    first = login(api, key="k" * 500)
    second = login(api, key="k" * 500)

    assert first.status_code == second.status_code == 200
    # Treated as though no key was sent at all.
    assert first.data["access"] != second.data["access"]


def test_login_still_works_when_the_cache_is_broken(api, staff, monkeypatch):
    """Idempotency is a convenience; it must never fail the login closed."""
    class BrokenCache:
        def get(self, *args, **kwargs):
            raise RuntimeError("cache table is missing")

        def set(self, *args, **kwargs):
            raise RuntimeError("cache table is missing")

    # Swap the module's reference rather than mutating the shared cache
    # object, which the throttle also uses.
    monkeypatch.setattr("apps.common.idempotency.cache", BrokenCache())

    response = login(api, key="retry-1")

    assert response.status_code == 200
    assert "access" in response.data


def test_a_non_staff_account_is_still_refused(api):
    get_user_model().objects.create_user(username="walker", password=PASSWORD)

    response = login(api, key="retry-1", username="walker")

    assert response.status_code == 400
