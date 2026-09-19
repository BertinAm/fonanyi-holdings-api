from rest_framework import viewsets
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny

from apps.common.permissions import ReadOnlyOrStaff

from .models import SiteSettings, Testimonial
from .serializers import SiteSettingsSerializer, TestimonialSerializer


class SiteSettingsView(RetrieveUpdateAPIView):
    serializer_class = SiteSettingsSerializer
    permission_classes = [ReadOnlyOrStaff]

    def get_object(self):
        return SiteSettings.load()


class TestimonialViewSet(viewsets.ModelViewSet):
    serializer_class = TestimonialSerializer
    permission_classes = [ReadOnlyOrStaff]
    filterset_fields = ["division", "is_featured"]
    search_fields = ["name", "role_business", "quote"]

    def get_queryset(self):
        qs = Testimonial.objects.all()
        user = self.request.user
        if not (user.is_authenticated and user.is_staff):
            qs = qs.filter(is_featured=True)
        return qs

    def get_permissions(self):
        if self.action in {"list", "retrieve"}:
            return [AllowAny()]
        return super().get_permissions()
