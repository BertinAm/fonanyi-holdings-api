from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "division", "status", "created_at"]
    list_filter = ["status", "division"]
    search_fields = ["full_name", "email", "message"]
    readonly_fields = ["created_at", "updated_at", "source_ip"]
