from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.siteinfo.urls")),
    path("api/", include("apps.gallery.urls")),
    path("api/", include("apps.blog.urls")),
    path("api/", include("apps.contact.urls")),
    path("api/", include("apps.careers.urls")),
    path("api/", include("apps.analytics.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
