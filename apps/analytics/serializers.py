from rest_framework import serializers

from .models import VisitEvent


class VisitEventCreateSerializer(serializers.ModelSerializer):
    """What a browser is allowed to report about itself.

    `kind` is restricted here rather than left to the model's choices. Sign-in
    and form events are written by the server when it sees them happen, and a
    stranger who could POST one would be able to invent a sign-in that never
    occurred, or bury a real one under noise.
    """

    class Meta:
        model = VisitEvent
        fields = ["kind", "path", "label", "referrer"]

    def validate_kind(self, value):
        if value not in VisitEvent.PUBLIC_KINDS:
            raise serializers.ValidationError(
                f"Only {', '.join(sorted(VisitEvent.PUBLIC_KINDS))} may be reported."
            )
        return value


class VisitEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitEvent
        fields = [
            "id", "kind", "kind_display", "path", "label", "referrer",
            "username", "created_at",
        ]

    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True, default=None)
