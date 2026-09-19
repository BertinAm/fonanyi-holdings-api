from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import MeView, StaffLoginView

urlpatterns = [
    path("auth/login/", StaffLoginView.as_view(), name="staff-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
]
