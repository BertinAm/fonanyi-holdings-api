import logging

from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.analytics.models import VisitEvent
from apps.analytics.record import record
from apps.common import idempotency

from .serializers import StaffTokenObtainPairSerializer

logger = logging.getLogger(__name__)


class StaffLoginView(TokenObtainPairView):
    serializer_class = StaffTokenObtainPairSerializer
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        """Safe to retry: a repeat with the same Idempotency-Key replays.

        The throttle check runs first either way, so a replay still costs the
        caller nothing and cannot be used to sidestep the rate limit: the key
        only ever returns a response that those exact credentials already
        earned.
        """
        key = idempotency.cache_key(request, scope="login")
        cached = idempotency.replay(key)
        if cached is not None:
            # A replay is the same sign-in, not a second one. Recording it
            # again would make one retried login look like two.
            return cached

        username = str(request.data.get("username", ""))[:150]
        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            # Bad credentials arrive as a raised AuthenticationFailed, which
            # DRF turns into a 401 further out. Recording only the returned
            # responses therefore counted every success and no failure -- the
            # half that actually matters.
            self._record(request, username, succeeded=False)
            raise

        self._record(request, username, succeeded=response.status_code < 400)
        idempotency.remember(key, response)
        return response

    @staticmethod
    def _record(request, username, *, succeeded):
        """Log the attempt. A failure here must not fail the sign-in."""
        user = None
        if username:
            # Resolved even on failure, so a run of failures against a real
            # account is distinguishable from noise against names that do not
            # exist. No password is involved in this lookup.
            user = get_user_model().objects.filter(username__iexact=username).first()
        record(
            request,
            VisitEvent.LOGIN if succeeded else VisitEvent.LOGIN_FAILED,
            path="/admin/login/",
            label=username or "(no username given)",
            user=user,
        )


class MeView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.get_full_name() or user.username,
                "is_superuser": user.is_superuser,
            }
        )
