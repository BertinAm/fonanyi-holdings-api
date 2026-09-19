from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SiteSettingsView, TestimonialViewSet

router = DefaultRouter()
router.register("testimonials", TestimonialViewSet, basename="testimonial")

urlpatterns = [
    path("site-settings/", SiteSettingsView.as_view(), name="site-settings"),
    path("", include(router.urls)),
]
