"""Clean the HTML that the article editor produces.

The dashboard writes HTML and the public site renders it, which means the
body of an article is the one place on this site where someone with a staff
login could put a script tag in front of every visitor. Sanitising in the
browser would not help: the API accepts whatever is POSTed to it, editor or
not. So it happens here, on the way in, once.

Allow-list, never deny-list. A deny-list is a guess at every dangerous thing
anyone will ever invent; an allow-list is a statement of what an article is
made of, and everything else is dropped.
"""
from __future__ import annotations

import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

# What an article can contain. Deliberately small: headings start at h2
# because the page already has the title as its h1, and a second h1 in the
# body breaks the document outline for screen readers and for search.
ALLOWED_TAGS = {
    "p", "br", "hr",
    # `strike` is here because that is what execCommand("strikeThrough")
    # actually emits in Chrome -- checked in a browser, not assumed. Without
    # it the toolbar button appeared to do nothing after a save.
    "strong", "b", "em", "i", "u", "s", "strike", "del", "mark", "sub", "sup",
    "h2", "h3", "h4",
    "ul", "ol", "li",
    "blockquote", "pre", "code",
    "a", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td",
    "span", "div",
}

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
    # Only the alignment the editor sets. Anything else in a style attribute
    # is dropped by the CSS sanitiser below.
    "p": ["style"],
    "h2": ["style"],
    "h3": ["style"],
    "h4": ["style"],
    "span": ["style"],
    "div": ["style"],
    "figure": ["style"],
}

# `data:` is not here on purpose. A data: image would be pasted straight into
# the database as base64, bloating every response that carries the article,
# and it is the usual way an image tag smuggles something that is not an
# image. Pictures go through the upload endpoint and come back as a URL.
ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel"]

CSS_SANITIZER = CSSSanitizer(allowed_css_properties=["text-align"])

# A body that came from the old plain-text editor, or from someone typing
# into the API directly. Detected rather than assumed so that existing
# articles keep their paragraph breaks instead of collapsing into one block.
HTML_TAG = re.compile(r"<(p|br|div|h[1-6]|ul|ol|li|blockquote|figure|img|strong|em)\b", re.I)

# bleach strips a tag but keeps what is inside it, which is right for <b> and
# wrong for <script>: the code would survive as visible prose in the article.
# Not a security control -- bleach already neutralises these, and if this
# pattern misses a variant the output is still safe -- it only keeps the text
# tidy, which is why a regex over HTML is acceptable here.
VOID_CONTENT = re.compile(
    r"<\s*(script|style|noscript|template|iframe|object|embed)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.I | re.S,
)


def looks_like_html(value: str) -> bool:
    return bool(HTML_TAG.search(value or ""))


def clean_html(value: str | None) -> str:
    """Return the value with everything not on the allow-list removed."""
    if not value:
        return ""

    cleaned = bleach.clean(
        VOID_CONTENT.sub("", value),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=CSS_SANITIZER,
        strip=True,
    )
    return _harden_links(cleaned).strip()


def _harden_links(html: str) -> str:
    """A link that opens a new tab hands that tab a reference back to ours.

    Without rel=noopener the opened page can navigate the original through
    window.opener. Added here rather than trusted to the editor, because the
    editor is not the only thing that can write to this field.
    """
    def fix(match: re.Match) -> str:
        tag = match.group(0)
        if 'target="_blank"' not in tag and "target='_blank'" not in tag:
            return tag
        if "rel=" in tag:
            return tag
        return tag[:-1].rstrip() + ' rel="noopener noreferrer">'

    return re.sub(r"<a\b[^>]*>", fix, html)


def to_html(value: str | None) -> str:
    """Plain text in, paragraphs out. Leaves real HTML alone.

    Articles written before the editor existed are plain text with blank
    lines between paragraphs. Rendering those as HTML without this would run
    every paragraph together into one wall of text.
    """
    if not value:
        return ""
    if looks_like_html(value):
        return clean_html(value)

    escaped = bleach.clean(value, tags=set(), attributes={}, strip=True)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", escaped) if p.strip()]
    return "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)
