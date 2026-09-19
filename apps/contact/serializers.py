from rest_framework import serializers

from .models import ContactMessage


class ContactMessageCreateSerializer(serializers.ModelSerializer):
    # Bots fill hidden fields; humans leave them empty.
    company_website = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "division",
            "subject",
            "message",
            "company_website",
        ]
        read_only_fields = ["id"]

    def validate_company_website(self, value):
        if value:
            raise serializers.ValidationError("Rejected.")
        return value

    def create(self, validated_data):
        validated_data.pop("company_website", None)
        request = self.context.get("request")
        if request is not None:
            validated_data["source_ip"] = _client_ip(request)
        return super().create(validated_data)


class ContactMessageAdminSerializer(serializers.ModelSerializer):
    division_label = serializers.CharField(source="get_division_display", read_only=True)

    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "division",
            "division_label",
            "subject",
            "message",
            "status",
            "created_at",
        ]
        read_only_fields = [f for f in fields if f != "status"]


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
