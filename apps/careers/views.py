from django.conf import settings
from django.core.mail import send_mail
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from .models import JobApplication
from .serializers import JobApplicationAdminSerializer, JobApplicationCreateSerializer


class JobApplicationCreateView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = JobApplication.objects.none()
    serializer_class = JobApplicationCreateSerializer
    permission_classes = [AllowAny]
    throttle_scope = "contact"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        _notify_staff(application)
        return Response(
            {"detail": "Application received.", "id": application.id},
            status=status.HTTP_201_CREATED,
        )


class JobApplicationAdminViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = JobApplication.objects.all()
    serializer_class = JobApplicationAdminSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["status", "role", "availability"]
    search_fields = ["full_name", "phone", "email", "about"]


def _notify_staff(application):
    recipient = getattr(settings, "CONTACT_NOTIFY_EMAIL", "")
    if not recipient:
        return
    try:
        send_mail(
            subject=f"[Fonanyi] Job application from {application.full_name}",
            message=(
                f"Name: {application.full_name}\n"
                f"Phone: {application.phone}\n"
                f"Email: {application.email}\n"
                f"Location: {application.location}\n"
                f"Role: {application.get_role_display()}\n"
                f"Availability: {application.get_availability_display()}\n"
                f"Experience: {application.years_experience} year(s)\n\n"
                f"{application.about}"
            ),
            from_email=None,
            recipient_list=[recipient],
            fail_silently=True,
        )
    except Exception:  # pragma: no cover - shared hosting SMTP is flaky
        pass
