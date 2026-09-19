from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.blog.models import Post
from apps.careers.models import JobApplication
from apps.contact.models import ContactMessage
from apps.gallery.models import GalleryImage
from apps.siteinfo.models import Testimonial

from .models import VisitEvent
from .serializers import VisitEventCreateSerializer, VisitEventSerializer


class TrackView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = VisitEvent.objects.none()
    serializer_class = VisitEventCreateSerializer
    permission_classes = [AllowAny]
    throttle_scope = "track"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:300]
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
            "REMOTE_ADDR", ""
        )
        serializer.save(
            user_agent=user_agent,
            visitor_hash=VisitEvent.make_visitor_hash(ip, user_agent, timezone.now().date()),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class VisitEventViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = VisitEvent.objects.all()
    serializer_class = VisitEventSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["kind"]


class DashboardSummaryView(APIView):
    """Everything the admin dashboard header needs, in one request."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        prev_week = now - timedelta(days=14)

        week_events = VisitEvent.objects.filter(created_at__gte=week_ago)
        views_this_week = week_events.filter(kind="page").count()
        views_prev_week = VisitEvent.objects.filter(
            kind="page", created_at__gte=prev_week, created_at__lt=week_ago
        ).count()
        visitors_this_week = week_events.values("visitor_hash").distinct().count()

        by_day = (
            week_events.filter(kind="page")
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        top_pages = (
            week_events.filter(kind="page")
            .values("path")
            .annotate(count=Count("id"))
            .order_by("-count")[:8]
        )

        return Response(
            {
                "gallery_count": GalleryImage.objects.filter(is_published=True).count(),
                "testimonial_count": Testimonial.objects.count(),
                "post_count": Post.objects.count(),
                "published_post_count": Post.objects.filter(is_published=True).count(),
                "new_message_count": ContactMessage.objects.filter(status="new").count(),
                "new_application_count": JobApplication.objects.filter(status="new").count(),
                "total_application_count": JobApplication.objects.count(),
                "total_message_count": ContactMessage.objects.count(),
                "views_this_week": views_this_week,
                "views_prev_week": views_prev_week,
                "visitors_this_week": visitors_this_week,
                "views_by_day": [
                    {"day": row["day"].isoformat(), "count": row["count"]} for row in by_day
                ],
                "top_pages": list(top_pages),
            }
        )
