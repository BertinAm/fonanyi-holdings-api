from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.common import idempotency

from .serializers import StaffTokenObtainPairSerializer


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
            return cached

        response = super().post(request, *args, **kwargs)
        idempotency.remember(key, response)
        return response


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
