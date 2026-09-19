from django.contrib import admin

from .models import GalleryImage


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ["__str__", "category", "is_published", "sort_order", "created_at"]
    list_filter = ["category", "is_published"]
    search_fields = ["title", "caption"]
