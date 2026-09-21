"""Somewhere for the article editor to put a picture.

The editor needs a URL before it can show an image in the body, so the file
has to be stored the moment it is dropped in -- before the article it belongs
to is saved, and possibly for an article that is never saved at all.

Staff only, and the file is validated as an image by decoding it rather than
by trusting its name or the Content-Type the browser sent. Both are supplied
by whoever is uploading.
"""
from __future__ import annotations

from django.core.files.storage import default_storage
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.images import compress

MAX_BYTES = 12 * 1024 * 1024


class EditorUploadView(APIView):
    """POST an image, get back a URL to put in the article body."""

    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file") or request.FILES.get("image")
        if upload is None:
            return Response(
                {"detail": "No file was sent."}, status=status.HTTP_400_BAD_REQUEST
            )
        if upload.size > MAX_BYTES:
            return Response(
                {"detail": f"That file is larger than {MAX_BYTES // (1024 * 1024)} MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Decoded, not sniffed by extension: a .jpg is only a JPEG because
        # Pillow can read it as one.
        try:
            Image.open(upload).verify()
        except Exception:
            return Response(
                {"detail": "That file is not an image we can read."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        upload.seek(0)

        # Same treatment as any other upload: staff paste straight off a
        # phone, and a 5 MB photo in the middle of an article is paid for by
        # every reader on mobile data.
        shrunk = compress(upload)
        name = f"blog/inline/{timezone.now():%Y/%m}/{shrunk.name}"
        stored = default_storage.save(name, shrunk)

        # Absolute, because the editor writes this straight into the article
        # body and the public site is served from a different origin.
        return Response(
            {"url": request.build_absolute_uri(default_storage.url(stored)), "path": stored},
            status=status.HTTP_201_CREATED,
        )
