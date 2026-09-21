"""The article body is the one field a staff login can aim at every reader.

The public page renders it as HTML, so what the sanitiser lets through is
what a visitor's browser executes. These tests are the record of what is
allowed, and the reason each refusal exists.
"""
from io import BytesIO

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.blog.models import Post
from apps.common.richtext import clean_html, to_html

pytestmark = pytest.mark.django_db


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def staff():
    return User.objects.create_user(username="ashu", password="long-enough-password", is_staff=True)


def auth(api, user):
    from rest_framework_simplejwt.tokens import RefreshToken

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return api


# ---- what survives ---------------------------------------------------------

@pytest.mark.parametrize(
    "html",
    [
        "<p>A plain paragraph.</p>",
        "<p><strong>Bold</strong> and <em>italic</em> and <u>underlined</u>.</p>",
        "<h2>A heading</h2><h3>And a smaller one</h3>",
        "<ul><li>One</li><li>Two</li></ul>",
        "<ol><li>First</li></ol>",
        "<blockquote><p>Quoted.</p></blockquote>",
        '<img src="https://api.example.com/media/x.jpg" alt="A canopy">',
        '<a href="https://example.com">A link</a>',
        '<p style="text-align:center">Centred</p>',
    ],
)
def test_the_editor_toolbar_output_survives(html):
    cleaned = clean_html(html)
    assert cleaned, f"{html} was removed entirely"


# ---- what does not ---------------------------------------------------------

def test_a_script_is_removed_with_its_contents():
    assert clean_html("<script>alert(1)</script><p>after</p>") == "<p>after</p>"


def test_an_event_handler_is_stripped():
    assert "onclick" not in clean_html('<p onclick="steal()">Hi</p>')


def test_a_javascript_url_is_refused():
    assert "javascript" not in clean_html('<a href="javascript:alert(1)">x</a>')


def test_a_data_uri_image_is_refused():
    """base64 in the body bloats every response and hides non-images."""
    assert "data:" not in clean_html('<img src="data:image/svg+xml;base64,PHN2Zz4=">')


@pytest.mark.parametrize("html", ["<iframe src='https://evil'></iframe>", "<svg onload=alert(1)>"])
def test_embedded_documents_are_refused(html):
    assert clean_html(html) == ""


def test_a_style_property_outside_the_allow_list_is_dropped():
    cleaned = clean_html('<p style="position:fixed;top:0">x</p>')
    assert "position" not in cleaned


def test_a_new_tab_link_cannot_reach_back_through_window_opener():
    cleaned = clean_html('<a href="https://x.example" target="_blank">x</a>')
    assert 'rel="noopener noreferrer"' in cleaned


# ---- articles written before the editor existed ----------------------------

def test_plain_text_keeps_its_paragraphs():
    html = to_html("First para.\n\nSecond para.")

    assert html.count("<p>") == 2


def test_a_single_newline_stays_inside_its_paragraph():
    assert to_html("Line one.\nLine two.") == "<p>Line one.<br>Line two.</p>"


def test_plain_text_is_escaped_not_executed():
    assert "<script>" not in to_html("Look: <script>alert(1)</script>")


def test_real_html_is_left_as_html():
    assert to_html("<p>Already <em>rich</em>.</p>") == "<p>Already <em>rich</em>.</p>"


# ---- the model and the API -------------------------------------------------

def test_saving_a_post_sanitises_it(staff):
    post = Post.objects.create(title="Hello", body='<p onclick="x()">Hi</p>')

    assert "onclick" not in post.body


def test_the_read_time_ignores_markup():
    words = " ".join(["word"] * 400)
    bare = Post.objects.create(title="Bare", body=words)
    tagged = Post.objects.create(title="Tagged", body=f"<p><strong>{words}</strong></p>")

    assert bare.read_minutes == tagged.read_minutes


def test_the_api_returns_render_ready_html(api, staff):
    Post.objects.create(title="Legacy", body="One.\n\nTwo.", is_published=True)

    body = api.get("/api/posts/legacy/").json()

    assert body["body_html"].count("<p>") == 2
    assert body["body"] == "One.\n\nTwo.", "the editor still loads what was typed"


# ---- the editor's image upload --------------------------------------------

def jpeg(name="inline.jpg"):
    buffer = BytesIO()
    Image.effect_noise((600, 400), 60).convert("RGB").save(buffer, "JPEG", quality=90)
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), "image/jpeg")


def test_staff_can_upload_an_image_for_the_body(api, staff, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path

    response = auth(api, staff).post(
        "/api/admin/editor-upload/", {"file": jpeg()}, format="multipart"
    )

    assert response.status_code == 201
    assert response.json()["url"].startswith("http")


def test_a_stranger_cannot_upload(api):
    assert api.post("/api/admin/editor-upload/", {"file": jpeg()}, format="multipart").status_code == 401


def test_a_file_that_is_not_an_image_is_refused(api, staff, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    disguised = SimpleUploadedFile("photo.jpg", b"<?php system($_GET[0]); ?>", "image/jpeg")

    response = auth(api, staff).post(
        "/api/admin/editor-upload/", {"file": disguised}, format="multipart"
    )

    assert response.status_code == 400


# ---- what the browser actually emits ---------------------------------------
# Captured by running document.execCommand in a real browser rather than
# reasoning about it. Two of these were broken when first written: strike was
# missing from the allow-list, and styleWithCSS produced spans whose style was
# stripped, losing the formatting silently.

@pytest.mark.parametrize(
    "emitted,must_keep",
    [
        ("<p><b>hello</b> world</p>", "<b>"),
        ("<p><i>hello</i> world</p>", "<i>"),
        ("<p><u>hello</u> world</p>", "<u>"),
        ("<p><strike>hello</strike> world</p>", "<strike>"),
        ('<p style="text-align: center;">hello</p>', "text-align"),
    ],
)
def test_the_toolbar_output_survives_a_round_trip(emitted, must_keep):
    assert must_keep in clean_html(emitted)


def test_invalid_list_nesting_from_execcommand_is_repaired():
    """execCommand wraps a new list in the paragraph it replaced."""
    cleaned = clean_html("<p><ul><li>a</li></ul></p>")

    assert "<ul><li>a</li></ul>" in cleaned


def test_a_css_styled_bold_is_recorded_as_lost():
    """styleWithCSS must stay off in the editor, and this is why.

    The span survives with an empty style, so the text is kept but the
    formatting is not. If this ever starts passing differently, check what
    RichTextEditor is setting before blaming the sanitiser.
    """
    cleaned = clean_html('<p><span style="font-weight: bold;">x</span></p>')

    assert "font-weight" not in cleaned
    assert "x" in cleaned
