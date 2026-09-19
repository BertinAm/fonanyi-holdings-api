import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from apps.careers.models import JobApplication

pytestmark = pytest.mark.django_db

VALID = {
    "full_name": "Ebong Tabi",
    "phone": "+237600000001",
    "role": "canopy",
    "availability": "weekends",
    "years_experience": 3,
    "about": "Three years putting up canopies for event companies around Buea.",
}


@pytest.fixture
def api():
    return APIClient()


def auth(api, user):
    from rest_framework_simplejwt.tokens import RefreshToken

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return api


def test_anyone_can_apply(api):
    response = api.post("/api/careers/", VALID, format="json")

    assert response.status_code == 201
    application = JobApplication.objects.get()
    assert application.full_name == "Ebong Tabi"
    assert application.status == "new"


def test_a_filled_honeypot_is_rejected(api):
    response = api.post(
        "/api/careers/", {**VALID, "company_website": "http://spam.example"}, format="json"
    )

    assert response.status_code == 400
    assert JobApplication.objects.count() == 0


def test_applications_are_not_publicly_readable(api):
    JobApplication.objects.create(**VALID)

    assert api.get("/api/careers/").status_code in (401, 403, 405)
    assert api.get("/api/admin/applications/").status_code in (401, 403)


def test_non_staff_cannot_read_applications(api):
    JobApplication.objects.create(**VALID)
    civilian = User.objects.create_user("civilian", password="pw")

    assert auth(api, civilian).get("/api/admin/applications/").status_code == 403


def test_staff_can_read_and_triage(api):
    application = JobApplication.objects.create(**VALID)
    staff = User.objects.create_user("staff", password="pw", is_staff=True)
    client = auth(api, staff)

    listed = client.get("/api/admin/applications/")
    assert listed.status_code == 200
    assert listed.json()["results"][0]["role_label"] == "Canopy setup crew"

    patched = client.patch(
        f"/api/admin/applications/{application.id}/", {"status": "shortlisted"}, format="json"
    )
    assert patched.status_code == 200
    application.refresh_from_db()
    assert application.status == "shortlisted"
