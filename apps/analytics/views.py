from collections import Counter
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings
from django.db.models import Count
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
from .record import record
from .serializers import VisitEventCreateSerializer, VisitEventSerializer


class TrackView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = VisitEvent.objects.none()
    serializer_class = VisitEventCreateSerializer
    permission_classes = [AllowAny]
    throttle_scope = "track"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        # Routed through record() so the address logic lives in one place.
        # This used to read X-Forwarded-For directly, which both trusted a
        # spoofable header and ignored CF-Connecting-IP.
        record(
            request,
            data["kind"],
            path=data.get("path", ""),
            label=data.get("label", ""),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class VisitEventViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = VisitEvent.objects.all()
    serializer_class = VisitEventSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["kind"]
    search_fields = ["path", "label", "referrer"]


class DashboardSummaryView(APIView):
    """Everything the admin dashboard needs, in one request.

    One endpoint rather than six: the dashboard opens on this, and six
    round trips from Buea over a mobile connection is a visibly slower
    screen than one.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        prev_week = now - timedelta(days=14)
        day_ago = now - timedelta(days=1)

        week_events = VisitEvent.objects.filter(created_at__gte=week_ago)
        prev_events = VisitEvent.objects.filter(
            created_at__gte=prev_week, created_at__lt=week_ago
        )

        views_this_week = week_events.filter(kind=VisitEvent.PAGE).count()
        views_prev_week = prev_events.filter(kind=VisitEvent.PAGE).count()
        visitors_this_week = (
            week_events.filter(kind=VisitEvent.PAGE).values("visitor_hash").distinct().count()
        )
        visitors_prev_week = (
            prev_events.filter(kind=VisitEvent.PAGE).values("visitor_hash").distinct().count()
        )

        by_day = self._views_by_day(week_events)
        top_pages = (
            week_events.filter(kind=VisitEvent.PAGE)
            .values("path")
            .annotate(count=Count("id"))
            .order_by("-count")[:8]
        )

        return Response(
            {
                # ---- content ----
                "gallery_count": GalleryImage.objects.filter(is_published=True).count(),
                "testimonial_count": Testimonial.objects.count(),
                "post_count": Post.objects.count(),
                "published_post_count": Post.objects.filter(is_published=True).count(),
                "new_message_count": ContactMessage.objects.filter(status="new").count(),
                "new_application_count": JobApplication.objects.filter(status="new").count(),
                "total_application_count": JobApplication.objects.count(),
                "total_message_count": ContactMessage.objects.count(),

                # ---- traffic ----
                "views_this_week": views_this_week,
                "views_prev_week": views_prev_week,
                "visitors_this_week": visitors_this_week,
                "visitors_prev_week": visitors_prev_week,
                "views_by_day": by_day,
                "top_pages": list(top_pages),
                "top_referrers": self._top_referrers(week_events),

                # ---- forms ----
                "form_submissions_this_week": week_events.filter(kind=VisitEvent.FORM).count(),
                "form_submissions_prev_week": prev_events.filter(kind=VisitEvent.FORM).count(),
                "forms_by_type": list(
                    week_events.filter(kind=VisitEvent.FORM)
                    .values("label")
                    .annotate(count=Count("id"))
                    .order_by("-count")
                ),
                # Of the people who looked, how many got in touch. Guarded
                # against a zero week, which is the normal state of a site
                # that has just launched.
                "conversion_rate": (
                    round(
                        week_events.filter(kind=VisitEvent.FORM).count()
                        / visitors_this_week * 100,
                        1,
                    )
                    if visitors_this_week
                    else 0.0
                ),

                # ---- who is getting in ----
                "logins_this_week": week_events.filter(kind=VisitEvent.LOGIN).count(),
                "failed_logins_this_week": week_events.filter(
                    kind=VisitEvent.LOGIN_FAILED
                ).count(),
                "failed_logins_today": VisitEvent.objects.filter(
                    kind=VisitEvent.LOGIN_FAILED, created_at__gte=day_ago
                ).count(),
                "recent_logins": self._recent_logins(),
            }
        )

    @staticmethod
    def _views_by_day(week_events):
        """Group page views by local date, in Python rather than in SQL.

        TruncDate with USE_TZ on MySQL emits
        CONVERT_TZ(created_at, 'UTC', 'Africa/Douala'), and that returns NULL
        unless the server has had its timezone tables loaded with
        mysql_tzinfo_to_sql -- which shared hosting does not do. Every row
        then came back with day=None and building the response raised, so the
        whole dashboard returned a 500 as soon as the first page view existed.

        SQLite implements the same conversion in Python, so the test suite
        never saw it. `manage.py check_analytics` reports whether this
        server can do the conversion at all.

        Reading one column for one week of traffic is cheap at this size. If
        the site ever gets busy enough for that to matter, the fix is a
        stored local date on the row, not CONVERT_TZ.
        """
        counts = Counter()
        for stamp in week_events.filter(kind=VisitEvent.PAGE).values_list(
            "created_at", flat=True
        ):
            counts[timezone.localtime(stamp).date()] += 1
        return [{"day": day.isoformat(), "count": n} for day, n in sorted(counts.items())]

    @staticmethod
    def _top_referrers(week_events):
        """Where visitors came from, with our own pages folded out.

        A visitor moving between pages on the site refers themselves, which
        would otherwise crowd out every real source.
        """
        rows = (
            week_events.filter(kind=VisitEvent.PAGE)
            .exclude(referrer="")
            .values("referrer")
            .annotate(count=Count("id"))
            .order_by("-count")[:40]
        )
        own = urlparse(getattr(settings, "FRONTEND_URL", "")).netloc
        folded = {}
        for row in rows:
            host = urlparse(row["referrer"]).netloc or row["referrer"]
            if own and host == own:
                continue
            folded[host] = folded.get(host, 0) + row["count"]
        ranked = sorted(folded.items(), key=lambda pair: -pair[1])[:6]
        return [{"referrer": host, "count": count} for host, count in ranked]

    @staticmethod
    def _recent_logins():
        rows = VisitEvent.objects.filter(
            kind__in=[VisitEvent.LOGIN, VisitEvent.LOGIN_FAILED]
        ).select_related("user")[:12]
        return [
            {
                "id": row.id,
                "username": (row.user.username if row.user else row.label),
                "succeeded": row.kind == VisitEvent.LOGIN,
                # A failed attempt against a name that does not exist is
                # worth telling apart from one against a real account.
                "known_account": row.user_id is not None,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]
