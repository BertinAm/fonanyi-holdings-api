from django.apps import AppConfig


class SiteinfoConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.siteinfo"

    def ready(self):
        from . import signals  # noqa: F401
