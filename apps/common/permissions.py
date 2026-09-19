from rest_framework.permissions import SAFE_METHODS, BasePermission


class ReadOnlyOrStaff(BasePermission):
    """Anyone may read the public site; only staff may change it."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)
