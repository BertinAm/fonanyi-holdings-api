from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class StaffTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Only staff may sign in to the dashboard."""

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_staff:
            raise serializers.ValidationError("This account cannot access the dashboard.")
        data["user"] = {
            "id": self.user.id,
            "username": self.user.username,
            "email": self.user.email,
            "full_name": self.user.get_full_name() or self.user.username,
            "is_superuser": self.user.is_superuser,
        }
        return data
