from rest_framework import viewsets
from rest_framework.permissions import AllowAny

from apps.common.permissions import ReadOnlyOrStaff

from .models import Post
from .serializers import PostDetailSerializer, PostListSerializer


class PostViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrStaff]
    lookup_field = "slug"
    filterset_fields = ["division", "is_published"]
    search_fields = ["title", "excerpt", "body"]
    ordering_fields = ["published_at", "created_at", "title"]

    def get_queryset(self):
        qs = Post.objects.all()
        user = self.request.user
        if not (user.is_authenticated and user.is_staff):
            qs = qs.filter(is_published=True)
        return qs

    def get_serializer_class(self):
        return PostListSerializer if self.action == "list" else PostDetailSerializer

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return super().get_permissions()
