from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import JobApplicationAdminViewSet, JobApplicationCreateView

router = DefaultRouter()
router.register("careers", JobApplicationCreateView, basename="careers")
router.register("admin/applications", JobApplicationAdminViewSet, basename="admin-application")

urlpatterns = [path("", include(router.urls))]
