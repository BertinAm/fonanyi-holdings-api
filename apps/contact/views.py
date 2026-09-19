from django.conf import settings
from django.core.mail import send_mail
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from .models import ContactMessage
from .serializers import ContactMessageAdminSerializer, ContactMessageCreateSerializer


class ContactMessageCreateView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = ContactMessage.objects.none()
    serializer_class = ContactMessageCreateSerializer
    permission_classes = [AllowAny]
    throttle_scope = "contact"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        _notify_staff(message)
        return Response(
            {"detail": "Message received.", "id": message.id},
            status=status.HTTP_201_CREATED,
        )


class ContactMessageAdminViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageAdminSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["status", "division"]
    search_fields = ["full_name", "email", "subject", "message"]


def _notify_staff(message):
    """Best effort e-mail alert; a mail failure must not lose the enquiry."""
    recipient = getattr(settings, "CONTACT_NOTIFY_EMAIL", "")
    if not recipient:
        return
    try:
        send_mail(
            subject=f"[Fonanyi] New enquiry from {message.full_name}",
            message=(
                f"Name: {message.full_name}\n"
                f"Email: {message.email}\n"
                f"Phone: {message.phone}\n"
                f"Division: {message.get_division_display()}\n\n"
                f"{message.message}"
            ),
            from_email=None,
            recipient_list=[recipient],
            fail_silently=True,
        )
    except Exception:  # pragma: no cover - shared hosting SMTP is flaky
        pass
