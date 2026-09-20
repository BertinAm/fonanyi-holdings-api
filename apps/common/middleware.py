"""Keep the API and its admin out of search results.

The public site handles its own indexing. Nothing served from this domain
should ever appear in a search result: not the JSON endpoints, which would
expose enquiry shapes and staff names to anyone searching, and least of all
/django-admin/, whose login page is an invitation.

A robots.txt cannot do this job here. The domain is proxied, and Cloudflare
serves its own managed robots.txt at /robots.txt, which overrides whatever
the origin would return. A response header is not overridable that way, and
Google honours X-Robots-Tag exactly as it honours the meta tag.

Media is deliberately left alone: those photographs are the company's own
work and are already published on the public site, so there is no reason to
hide them from image search.
"""

NOINDEX = "noindex, nofollow, noarchive, nosnippet"

# Served straight off disk by LiteSpeed, so this middleware never sees them
# anyway. Listed for the reader, and so a change of layout does not silently
# start tagging them.
SKIP_PREFIXES = ("/media/",)


class NoIndexMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith(SKIP_PREFIXES):
            response.headers.setdefault("X-Robots-Tag", NOINDEX)
        return response
