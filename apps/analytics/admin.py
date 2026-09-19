from django.contrib import admin

from .models import VisitEvent


@admin.register(VisitEvent)
class VisitEventAdmin(admin.ModelAdmin):
    list_display = ["kind", "path", "label", "created_at"]
    list_filter = ["kind"]
    search_fields = ["path", "label"]
