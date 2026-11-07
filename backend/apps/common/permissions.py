from rest_framework import permissions
from apps.authorization.services import has_group_permission

class IsPlatformSuperAdmin(permissions.BasePermission):
    """Allows access only to authenticated users with is_platform_admin=True."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            from rest_framework.exceptions import NotAuthenticated
            raise NotAuthenticated("Authentication credentials were not provided.")

        if not (request.user.is_active and request.user.is_platform_admin and request.user.account_status != 'SUSPENDED'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Platform Super Admin privileges required.")

        return True


class HasGroupScopePermission(permissions.BasePermission):
    """
    Checks that the user holds a specific group permission.
    The view must provide get_group() or have group_id / pk in kwargs.
    """
    required_permission: str = ""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not request.user.is_active:
            return False

        if request.user.account_status == 'SUSPENDED':
            return False

        group = None
        if hasattr(view, 'get_group'):
            group = view.get_group()
        elif 'group_id' in view.kwargs:
            from apps.groups.models import EqubGroup
            try:
                group = EqubGroup.objects.get(id=view.kwargs['group_id'])
            except (EqubGroup.DoesNotExist, ValueError):
                return False

        if not group:
            return True # Let object-level check handle it if group is not in kwargs

        perm = getattr(view, 'required_permission', self.required_permission)
        if not perm:
            return True

        return has_group_permission(request.user, group, perm)
