import logging

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response

from apps.analytics.models import VisitEvent
from apps.analytics.record import record

from .models import ContactMessage
from .serializers import ContactMessageAdminSerializer, ContactMessageCreateSerializer

logger = logging.getLogger(__name__)



class ContactMessageCreateView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = ContactMessage.objects.none()
    serializer_class = ContactMessageCreateSerializer
    permission_classes = [AllowAny]
    throttle_scope = "contact"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        # Counted as an event as well as a row, so the dashboard can show
        # enquiries over time next to the traffic that produced them.
        record(request, VisitEvent.FORM, path="/contact/", label="Contact enquiry")
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
            fail_silently=False,
        )
    except Exception:  # pragma: no cover - shared hosting SMTP is flaky
        # The enquiry is already saved. Losing the alert is survivable;
        # losing it *silently* is not, because nobody would ever find out
        # that the notifications had stopped.
        logger.warning(
            "Could not e-mail the enquiry alert for %s", message.full_name, exc_info=True
        )
