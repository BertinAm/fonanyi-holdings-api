from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import StaffTokenObtainPairSerializer


class StaffLoginView(TokenObtainPairView):
    serializer_class = StaffTokenObtainPairSerializer
    throttle_scope = "login"


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
