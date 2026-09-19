from rest_framework import serializers

from apps.common.mixins_sanitise import SanitisedSubmissionSerializer

from .models import JobApplication

# `about` is a TextField; same reasoning as the contact message.
ABOUT_MAX = 2500


class JobApplicationCreateSerializer(SanitisedSubmissionSerializer):
    # Bots fill hidden fields; people leave them empty.
    company_website = serializers.CharField(required=False, allow_blank=True, write_only=True)
    about = serializers.CharField(max_length=ABOUT_MAX, trim_whitespace=False)

    LINE_FIELDS = ("full_name", "phone", "location")
    TEXT_FIELDS = ("about",)
    REQUIRED_AFTER_CLEAN = ("full_name", "phone", "about")

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "full_name",
            "phone",
            "email",
            "location",
            "role",
            "availability",
            "years_experience",
            "about",
            "company_website",
        ]
        read_only_fields = ["id"]

    def validate_company_website(self, value):
        if value:
            raise serializers.ValidationError("Rejected.")
        return value


class JobApplicationAdminSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    availability_label = serializers.CharField(source="get_availability_display", read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "full_name",
            "phone",
            "email",
            "location",
            "role",
            "role_label",
            "availability",
            "availability_label",
            "years_experience",
            "about",
            "status",
            "created_at",
        ]
        read_only_fields = [f for f in fields if f != "status"]
