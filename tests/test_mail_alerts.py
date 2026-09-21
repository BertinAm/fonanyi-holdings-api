"""A failed alert must never lose the submission, and never be silent.

Those two pull in opposite directions. The form has to succeed even when the
mail server does not, but if the failure leaves no trace, the alerts can stop
arriving and nobody finds out until someone asks why nobody replied.
"""
import logging

import pytest
from django.core import mail
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.careers.models import JobApplication
from apps.contact.models import ContactMessage

pytestmark = pytest.mark.django_db


CONTACT = {
    "full_name": "Ndive Mbua",
    "email": "ndive@example.com",
    "division": "energy",
    "message": "Do you have forty chairs free on the 12th?",
}

APPLICATION = {
    "full_name": "Ekema Lyonga",
    "email": "ekema@example.com",
    "phone": "+237600000001",
    "role": "canopy",
    "availability": "weekends",
    "years_experience": 3,
    "about": "Three years wiring solar installations around Buea.",
}


@pytest.fixture
def api():
    return APIClient()


def test_an_enquiry_is_saved_and_an_alert_is_sent(api, settings):
    settings.CONTACT_NOTIFY_EMAIL = "info@example.com"
    response = api.post("/api/contact/", CONTACT, format="json")

    assert response.status_code == 201
    assert ContactMessage.objects.filter(email=CONTACT["email"]).exists()
    assert len(mail.outbox) == 1
    assert CONTACT["full_name"] in mail.outbox[0].subject
    assert mail.outbox[0].to == ["info@example.com"]


def test_an_application_is_saved_and_an_alert_is_sent(api, settings):
    settings.CONTACT_NOTIFY_EMAIL = "info@example.com"
    response = api.post("/api/careers/", APPLICATION, format="json")

    assert response.status_code == 201
    assert JobApplication.objects.filter(email=APPLICATION["email"]).exists()
    assert len(mail.outbox) == 1
    assert APPLICATION["full_name"] in mail.outbox[0].subject


@pytest.mark.parametrize(
    "url,payload,model,noun",
    [
        ("/api/contact/", CONTACT, ContactMessage, "enquiry"),
        ("/api/careers/", APPLICATION, JobApplication, "application"),
    ],
)
def test_a_broken_mail_server_neither_loses_nor_hides(
    api, settings, monkeypatch, caplog, url, payload, model, noun
):
    settings.CONTACT_NOTIFY_EMAIL = "info@example.com"

    def explode(*args, **kwargs):
        raise OSError("connection refused")

    # Patched where it is looked up, not where it is defined.
    module = "apps.contact.views" if model is ContactMessage else "apps.careers.views"
    monkeypatch.setattr(f"{module}.send_mail", explode)

    with caplog.at_level(logging.WARNING):
        response = api.post(url, payload, format="json")

    # The visitor is not punished for the mail server being down.
    assert response.status_code == 201
    assert model.objects.filter(email=payload["email"]).exists()

    # But the failure is on the record.
    assert any(
        noun in record.message and payload["full_name"] in str(record.args or record.message)
        for record in caplog.records
    ), f"no warning logged for the failed {noun} alert"


def test_no_recipient_means_no_mail_and_no_error(api, settings):
    settings.CONTACT_NOTIFY_EMAIL = ""
    response = api.post("/api/contact/", CONTACT, format="json")

    assert response.status_code == 201
    assert mail.outbox == []


def test_check_email_never_prints_the_password(settings, capsys):
    settings.EMAIL_HOST = "localhost"
    settings.EMAIL_HOST_PASSWORD = "hunter2-but-longer"
    settings.EMAIL_HOST_USER = "noreply@example.com"
    settings.CONTACT_NOTIFY_EMAIL = "info@example.com"

    call_command("check_email")

    captured = capsys.readouterr()
    assert "hunter2-but-longer" not in captured.out + captured.err
    # Its length is enough to tell a missing value from one that failed to
    # parse out of .env.
    assert "18 characters" in captured.out


def test_a_local_password_is_not_reported_as_a_problem(settings, capsys):
    """Whether the relay offers AUTH is a fact about the server.

    This was reported as a configuration problem on the assumption that a
    local relay never authenticates. The production relay does, and the
    warning sent someone to blank a password that was working.
    """
    settings.EMAIL_HOST = "localhost"
    settings.EMAIL_HOST_PASSWORD = "a-working-password"
    settings.EMAIL_HOST_USER = "noreply@example.com"
    settings.CONTACT_NOTIFY_EMAIL = "info@example.com"

    call_command("check_email")

    assert "offers no AUTH" not in capsys.readouterr().err


def test_a_missing_recipient_is_still_reported(settings, capsys):
    settings.EMAIL_HOST = "localhost"
    settings.EMAIL_HOST_USER = "noreply@example.com"
    settings.CONTACT_NOTIFY_EMAIL = ""

    call_command("check_email")

    assert "CONTACT_NOTIFY_EMAIL is not set" in capsys.readouterr().err
