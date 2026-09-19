from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DashboardSummaryView, TrackView, VisitEventViewSet

router = DefaultRouter()
router.register("track", TrackView, basename="track")
router.register("admin/visits", VisitEventViewSet, basename="admin-visit")

urlpatterns = [
    path("admin/summary/", DashboardSummaryView.as_view(), name="admin-summary"),
    path("", include(router.urls)),
]
