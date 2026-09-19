from rest_framework import serializers

from apps.common.mixins import AbsoluteImageMixin

from .models import GalleryImage


class GalleryImageSerializer(AbsoluteImageMixin, serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    thumb_url = serializers.SerializerMethodField()

    class Meta:
        model = GalleryImage
        fields = [
            "id",
            "title",
            "caption",
            "category",
            "image",
            "image_url",
            "thumb_url",
            "alt_text",
            "is_published",
            "sort_order",
            "created_at",
        ]
        extra_kwargs = {"image": {"write_only": True}}

    def get_image_url(self, obj):
        return self.absolute(obj.image)

    def get_thumb_url(self, obj):
        # Fall back to the full image so a row created before thumbnails
        # existed still renders rather than showing a gap.
        return self.absolute(obj.thumbnail) or self.absolute(obj.image)
