from rest_framework import serializers

from apps.common.mixins import AbsoluteImageMixin

from .models import Post


class PostListSerializer(AbsoluteImageMixin, serializers.ModelSerializer):
    cover_image_url = serializers.SerializerMethodField()
    division_label = serializers.CharField(source="get_division_display", read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "title",
            "slug",
            "excerpt",
            "cover_image_url",
            "division",
            "division_label",
            "author_name",
            "is_published",
            "published_at",
            "scheduled_for",
            "read_minutes",
        ]

    def get_cover_image_url(self, obj):
        return self.absolute(obj.cover_image)


class PostDetailSerializer(PostListSerializer):
    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + ["body", "cover_image", "created_at", "updated_at"]
        extra_kwargs = {"cover_image": {"write_only": True, "required": False}}
