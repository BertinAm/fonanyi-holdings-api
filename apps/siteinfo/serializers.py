from rest_framework import serializers

from apps.common.mixins import AbsoluteImageMixin

from .models import SiteSettings, Testimonial


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        exclude = ["id", "created_at", "updated_at"]


class TestimonialSerializer(AbsoluteImageMixin, serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = Testimonial
        fields = [
            "id",
            "name",
            "role_business",
            "quote",
            "division",
            "rating",
            "avatar",
            "avatar_url",
            "is_featured",
            "sort_order",
            "created_at",
        ]
        extra_kwargs = {"avatar": {"write_only": True, "required": False}}

    def get_avatar_url(self, obj):
        return self.absolute(obj.avatar)
