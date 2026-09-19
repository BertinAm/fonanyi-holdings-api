from rest_framework import serializers

from .models import VisitEvent


class VisitEventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitEvent
        fields = ["kind", "path", "label", "referrer"]


class VisitEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitEvent
        fields = ["id", "kind", "path", "label", "referrer", "created_at"]
