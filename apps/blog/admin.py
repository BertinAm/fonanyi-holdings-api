from django.contrib import admin

from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ["title", "division", "is_published", "published_at"]
    list_filter = ["division", "is_published"]
    search_fields = ["title", "body"]
    prepopulated_fields = {"slug": ("title",)}
