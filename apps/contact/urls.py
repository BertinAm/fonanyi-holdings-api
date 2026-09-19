from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ContactMessageAdminViewSet, ContactMessageCreateView

router = DefaultRouter()
router.register("contact", ContactMessageCreateView, basename="contact")
router.register("admin/messages", ContactMessageAdminViewSet, basename="admin-message")

urlpatterns = [path("", include(router.urls))]
