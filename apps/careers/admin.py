from django.contrib import admin

from .models import JobApplication


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ["full_name", "role", "availability", "status", "created_at"]
    list_filter = ["status", "role", "availability"]
    search_fields = ["full_name", "phone", "email", "about"]
    readonly_fields = ["created_at", "updated_at", "source_ip"]
