import pytest
from rest_framework.test import APIClient

from apps.contact.models import ContactMessage

pytestmark = pytest.mark.django_db

VALID = {
    "full_name": "Ngozi Ashu",
    "email": "ngozi@example.com",
    "division": "energy",
    "message": "Canopies for 200 guests on the 12th.",
}


@pytest.fixture
def api():
    return APIClient()


def test_a_visitor_can_send_an_enquiry(api):
    response = api.post("/api/contact/", VALID, format="json")

    assert response.status_code == 201
    message = ContactMessage.objects.get()
    assert message.full_name == "Ngozi Ashu"
    assert message.status == "new"


def test_a_filled_honeypot_is_rejected(api):
    response = api.post(
        "/api/contact/", {**VALID, "company_website": "http://spam.example"}, format="json"
    )

    assert response.status_code == 400
    assert ContactMessage.objects.count() == 0


def test_the_honeypot_value_is_never_stored(api):
    api.post("/api/contact/", {**VALID, "company_website": ""}, format="json")

    assert ContactMessage.objects.count() == 1


def test_enquiries_are_not_publicly_listable(api):
    ContactMessage.objects.create(**VALID)

    # The public router only exposes create; listing is a separate staff route.
    assert api.get("/api/contact/").status_code in (401, 403, 405)
