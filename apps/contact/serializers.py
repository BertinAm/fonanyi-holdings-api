from rest_framework import serializers

from apps.common.mixins_sanitise import SanitisedSubmissionSerializer

from .models import ContactMessage

# `message` is a TextField, so without a ceiling here a single POST can store
# as much as the request body allows.
MESSAGE_MAX = 4000


class ContactMessageCreateSerializer(SanitisedSubmissionSerializer):
    # Bots fill hidden fields; humans leave them empty.
    company_website = serializers.CharField(required=False, allow_blank=True, write_only=True)
    message = serializers.CharField(max_length=MESSAGE_MAX, trim_whitespace=False)

    LINE_FIELDS = ("full_name", "phone", "subject")
    TEXT_FIELDS = ("message",)
    REQUIRED_AFTER_CLEAN = ("full_name", "message")

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
