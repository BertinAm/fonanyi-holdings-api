from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .uploads import EditorUploadView
from .views import PostViewSet

router = DefaultRouter()
router.register("posts", PostViewSet, basename="post")

urlpatterns = [
    # Staff only. Sits outside the router because it is not a resource: it
    # takes a file and hands back a URL.
    path("admin/editor-upload/", EditorUploadView.as_view(), name="editor-upload"),
    path("", include(router.urls)),
]
