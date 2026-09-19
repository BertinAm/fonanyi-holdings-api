from rest_framework import serializers

from apps.contact.serializers import _client_ip

from .models import JobApplication


class JobApplicationCreateSerializer(serializers.ModelSerializer):
    # Bots fill hidden fields; people leave them empty.
    company_website = serializers.CharField(required=False, allow_blank=True, write_only=True)

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

    def create(self, validated_data):
        validated_data.pop("company_website", None)
        request = self.context.get("request")
        if request is not None:
            validated_data["source_ip"] = _client_ip(request)
        return super().create(validated_data)


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
