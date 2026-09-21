"""What the site records about itself.

Two things matter here beyond the counting. A visitor must not be able to
report an event the server is supposed to witness -- otherwise a sign-in can
be invented -- and recording must never be the reason a request fails.
"""
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.analytics.models import VisitEvent

pytestmark = pytest.mark.django_db


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def staff():
    return User.objects.create_user(
        username="tabi", password="a-long-enough-password", is_staff=True
    )


def auth(api, user):
    from rest_framework_simplejwt.tokens import RefreshToken

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return api


# ---- what the public may report -------------------------------------------

@pytest.mark.parametrize("kind", ["page", "link"])
def test_a_browser_may_report_its_own_traffic(api, kind):
    response = api.post("/api/track/", {"kind": kind, "path": "/gallery/"}, format="json")

    assert response.status_code == 204
    assert VisitEvent.objects.filter(kind=kind).count() == 1


@pytest.mark.parametrize("kind", ["login", "login_bad", "form"])
def test_a_browser_may_not_invent_a_server_side_event(api, kind):
    response = api.post("/api/track/", {"kind": kind, "path": "/"}, format="json")

    assert response.status_code == 400
    assert VisitEvent.objects.count() == 0


def test_a_visitor_hash_does_not_contain_the_address(api):
    api.post("/api/track/", {"kind": "page", "path": "/"}, format="json",
             REMOTE_ADDR="41.202.207.9")

    event = VisitEvent.objects.get()
    assert "41.202.207.9" not in event.visitor_hash
    assert len(event.visitor_hash) == 64


# ---- sign-ins --------------------------------------------------------------

def test_a_successful_sign_in_is_recorded_against_the_user(api, staff):
    response = api.post(
        "/api/auth/login/",
        {"username": "tabi", "password": "a-long-enough-password"},
        format="json",
    )

    assert response.status_code == 200
    event = VisitEvent.objects.get(kind=VisitEvent.LOGIN)
    assert event.user == staff


def test_a_failed_sign_in_against_a_real_account_is_distinguishable(api, staff):
    api.post("/api/auth/login/", {"username": "tabi", "password": "wrong"}, format="json")

    event = VisitEvent.objects.get(kind=VisitEvent.LOGIN_FAILED)
    assert event.user == staff, "a failure against a real account should name it"


def test_a_failed_sign_in_against_an_unknown_name_records_no_user(api):
    api.post("/api/auth/login/", {"username": "nobody", "password": "wrong"}, format="json")

    event = VisitEvent.objects.get(kind=VisitEvent.LOGIN_FAILED)
    assert event.user is None
    assert event.label == "nobody"


def test_no_password_is_ever_stored(api, staff):
    api.post(
        "/api/auth/login/",
        {"username": "tabi", "password": "a-long-enough-password"},
        format="json",
    )

    for event in VisitEvent.objects.all():
        blob = f"{event.label}{event.path}{event.referrer}{event.user_agent}"
        assert "a-long-enough-password" not in blob


# ---- forms -----------------------------------------------------------------

CONTACT = {
    "full_name": "Ngozi Ashu",
    "email": "ngozi@example.com",
    "division": "energy",
    "message": "Canopies for 200 guests on the 12th.",
}


def test_a_contact_enquiry_is_counted_as_a_form_event(api):
    api.post("/api/contact/", CONTACT, format="json")

    event = VisitEvent.objects.get(kind=VisitEvent.FORM)
    assert event.label == "Contact enquiry"


def test_a_recording_failure_does_not_lose_the_enquiry(api):
    with patch("apps.analytics.record.VisitEvent.objects.create", side_effect=OSError("db gone")):
        response = api.post("/api/contact/", CONTACT, format="json")

    from apps.contact.models import ContactMessage

    assert response.status_code == 201
    assert ContactMessage.objects.count() == 1


# ---- the summary -----------------------------------------------------------

def test_the_summary_reports_the_new_figures(api, staff):
    api.post("/api/contact/", CONTACT, format="json")
    api.post("/api/auth/login/", {"username": "tabi", "password": "wrong"}, format="json")
    api.post("/api/track/", {"kind": "page", "path": "/"}, format="json")

    body = auth(api, staff).get("/api/admin/summary/").json()

    assert body["form_submissions_this_week"] == 1
    assert body["failed_logins_this_week"] == 1
    assert body["views_this_week"] == 1
    assert {"label": "Contact enquiry", "count": 1} in body["forms_by_type"]
    assert body["recent_logins"][0]["succeeded"] is False
    assert body["recent_logins"][0]["known_account"] is True


def test_conversion_rate_survives_a_week_with_no_visitors(api, staff):
    body = auth(api, staff).get("/api/admin/summary/").json()

    assert body["conversion_rate"] == 0.0


def test_the_summary_stays_staff_only(api):
    assert api.get("/api/admin/summary/").status_code == 401
