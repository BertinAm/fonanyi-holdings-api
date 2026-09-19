import pytest
from rest_framework.test import APIClient

from apps.careers.models import JobApplication
from apps.common.sanitize import clean_line, clean_text, client_ip
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


# ---- the helpers themselves -------------------------------------------------

def test_clean_line_folds_a_newline_into_a_space():
    # The words either side must not run together once the break is gone.
    assert clean_line("Subject\r\nBcc: someone@example.com") == (
        "Subject Bcc: someone@example.com"
    )


def test_clean_line_drops_control_and_zero_width_characters():
    assert clean_line("Hello\x00\x07 world") == "Hello world"
    assert clean_line("Ngozi​ Ashu") == "Ngozi Ashu"


def test_clean_line_drops_a_bidi_override():
    # These are used to make a stored string render as something else.
    assert clean_line("‮evil‬") == "evil"


def test_clean_text_keeps_paragraphs_but_caps_blank_runs():
    assert clean_text("a\r\n\r\n\r\n\r\nb   \nc  ") == "a\n\nb\nc"


def test_clean_text_keeps_tabs_and_newlines():
    assert clean_text("keeps\ttabs\nand breaks\x00") == "keeps\ttabs\nand breaks"


# ---- client_ip --------------------------------------------------------------

def test_client_ip_ignores_a_forwarded_header_by_default(rf, settings):
    settings.TRUST_PROXY_HEADER = False
    request = rf.post("/", HTTP_X_FORWARDED_FOR="1.2.3.4", REMOTE_ADDR="10.0.0.9")

    assert client_ip(request) == "10.0.0.9"


def test_client_ip_reads_the_forwarded_header_when_trusted(rf, settings):
    settings.TRUST_PROXY_HEADER = True
    request = rf.post("/", HTTP_X_FORWARDED_FOR="1.2.3.4, 10.0.0.1", REMOTE_ADDR="10.0.0.9")

    assert client_ip(request) == "1.2.3.4"


def test_client_ip_returns_none_for_a_junk_address(rf, settings):
    # Writing this straight through to a GenericIPAddressField would raise on
    # save, turning a spoofed header into a 500.
    settings.TRUST_PROXY_HEADER = True
    request = rf.post("/", HTTP_X_FORWARDED_FOR="not-an-ip", REMOTE_ADDR="also-junk")

    assert client_ip(request) is None


# ---- applied to the public forms -------------------------------------------

def test_a_submitted_name_is_cleaned_before_it_is_stored(api):
    response = api.post(
        "/api/contact/",
        {**VALID, "full_name": "  Ngozi​   Ashu\r\nX: y  "},
        format="json",
    )

    assert response.status_code == 201
    assert ContactMessage.objects.get().full_name == "Ngozi Ashu X: y"


def test_a_name_that_cleans_down_to_nothing_is_rejected(api):
    response = api.post(
        "/api/contact/", {**VALID, "full_name": "​‮ \x00"}, format="json"
    )

    assert response.status_code == 400
    assert "full_name" in response.data
    assert not ContactMessage.objects.exists()


def test_an_oversized_message_is_rejected(api):
    response = api.post("/api/contact/", {**VALID, "message": "x" * 4001}, format="json")

    assert response.status_code == 400
    assert "message" in response.data


def test_a_message_at_the_limit_is_accepted(api):
    response = api.post("/api/contact/", {**VALID, "message": "x" * 4000}, format="json")

    assert response.status_code == 201


def test_an_oversized_application_is_rejected(api):
    response = api.post(
        "/api/careers/",
        {"full_name": "Eta Mbu", "phone": "+237670000000", "about": "x" * 2501},
        format="json",
    )

    assert response.status_code == 400
    assert "about" in response.data
    assert not JobApplication.objects.exists()


def test_an_application_is_cleaned_too(api):
    response = api.post(
        "/api/careers/",
        {"full_name": "  Eta​  Mbu ", "phone": " +237 670 000 000 ", "about": "Canopies.\r\n\r\n\r\nFive years."},
        format="json",
    )

    assert response.status_code == 201
    application = JobApplication.objects.get()
    assert application.full_name == "Eta Mbu"
    assert application.phone == "+237 670 000 000"
    assert application.about == "Canopies.\n\nFive years."
