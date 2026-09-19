from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from apps.common.permissions import ReadOnlyOrStaff

from .models import GalleryImage
from .serializers import GalleryImageSerializer


class GalleryImageViewSet(viewsets.ModelViewSet):
    serializer_class = GalleryImageSerializer
    permission_classes = [ReadOnlyOrStaff]
    filterset_fields = ["category", "is_published"]
    search_fields = ["title", "caption"]
    ordering_fields = ["sort_order", "created_at"]

    def get_queryset(self):
        qs = GalleryImage.objects.all()
        user = self.request.user
        if not (user.is_authenticated and user.is_staff):
            qs = qs.filter(is_published=True)
        return qs

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return super().get_permissions()
