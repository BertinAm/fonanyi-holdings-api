from django.contrib import admin

from .models import ContentFlag, SiteSettings, Testimonial


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ["company_name", "phone_primary", "email"]


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["name", "division", "rating", "is_featured", "sort_order"]
    list_filter = ["division", "is_featured"]
    search_fields = ["name", "quote"]


@admin.register(ContentFlag)
class ContentFlagAdmin(admin.ModelAdmin):
    list_display = ["__str__", "is_dirty", "last_rebuild_at"]
