class AbsoluteImageMixin:
    """Serializer helper that turns an ImageField into an absolute URL.

    The frontend is served from Cloudflare on a different origin, so relative
    media paths from Django are useless to it.
    """

    def absolute(self, image):
        if not image:
            return None
        request = self.context.get("request")
        url = image.url
        if request is not None:
            return request.build_absolute_uri(url)
        from django.conf import settings

        return f"{settings.SITE_URL.rstrip('/')}{url}"
