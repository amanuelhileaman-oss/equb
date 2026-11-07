import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class PermissionCatalog(models.Model):
    codename = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=50, db_index=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'permission_catalog'
        ordering = ['category', 'codename']
        verbose_name = _('permission')
        verbose_name_plural = _('permissions')

    def __str__(self):
        return f"{self.category}: {self.codename}"


class GroupRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='custom_roles',
        help_text=_("Null for global system role templates; set for group-specific custom roles.")
    )
    code = models.CharField(max_length=60, db_index=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=False)
    permissions = models.ManyToManyField(PermissionCatalog, related_name='roles', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'group_roles'
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'code'],
                name='unique_role_code_per_group'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class MembershipRoleAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membership = models.ForeignKey(
        'groups.GroupMembership',
        on_delete=models.CASCADE,
        related_name='role_assignments'
    )
    role = models.ForeignKey(GroupRole, on_delete=models.CASCADE, related_name='assignments')
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='roles_assigned'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'membership_role_assignments'
        constraints = [
            models.UniqueConstraint(
                fields=['membership', 'role'],
                name='unique_membership_role_assignment'
            )
        ]

    def __str__(self):
        return f"{self.membership.user.full_name} -> {self.role.name}"
