from typing import Optional
from django.db.models import Q
from .models import PermissionCatalog, GroupRole, MembershipRoleAssignment

# Standard permission catalog entries
DEFAULT_PERMISSIONS = [
    # Platform
    ('platform:manage_settings', 'Manage platform settings', 'platform'),
    ('platform:manage_plans', 'Manage SaaS subscription plans', 'platform'),
    ('platform:manage_subscriptions', 'Manage organizer subscriptions and invoices', 'platform'),
    ('platform:review_verification', 'Review organizer and group verifications', 'platform'),
    ('platform:view_audit_logs', 'View platform-wide security and audit logs', 'platform'),
    # Group & Members
    ('group:manage', 'Manage group settings and lifecycle', 'group'),
    ('group:manage_members', 'Invite, approve, or remove group members', 'group'),
    ('group:propose_rules', 'Propose new rules or amendments', 'group'),
    ('group:approve_rules', 'Vote/approve proposed rules', 'group'),
    ('group:view_reports', 'View group financial reports and summary', 'group'),
    # Financial & Contributions
    ('contributions:view', 'View contribution obligations and history', 'contributions'),
    ('contributions:record_cash', 'Record cash receipts from members', 'payments'),
    ('cash_payments:record', 'Record cash receipts from members', 'payments'),
    ('payments:view', 'View payments and transaction records', 'payments'),
    ('payments:reconcile', 'Reconcile bank/telebirr transfers and digital payments', 'payments'),
    ('payments:match', 'Match bank and digital payments to obligations', 'payments'),
    ('payments:flag_exception', 'Flag reconciliation exceptions and discrepancies', 'payments'),
    ('receipts:view', 'View member contribution receipts', 'payments'),
    ('receipts:issue', 'Issue contribution cash receipts', 'payments'),
    ('payment_adjustments:approve', 'Approve manual financial adjustments and corrections', 'payments'),
    ('financial_reports:view', 'View group financial reports and accounting summaries', 'reports'),
    # Payouts
    ('payouts:view', 'View scheduled and past group payouts', 'payouts'),
    ('payouts:prepare', 'Prepare group payout requests', 'payouts'),
    ('payouts:request', 'Request or initiate payout disbursement', 'payouts'),
    ('payouts:approve', 'Approve payout disbursement independently', 'payouts'),
    ('payouts:record_execution', 'Record settlement and bank execution evidence for payout', 'payouts'),
    # Disputes & Announcements
    ('disputes:manage', 'Review and resolve member disputes', 'disputes'),
    ('disputes:view_financial', 'View financial dispute records', 'disputes'),
    ('announcements:view', 'View group announcements', 'group'),
]

SYSTEM_ROLE_PERMISSIONS = {
    'GROUP_ORGANIZER': [
        'group:manage',
        'group:manage_members',
        'group:propose_rules',
        'group:approve_rules',
        'group:view_reports',
        'contributions:view',
        'payouts:request',
        'disputes:manage',
        'announcements:view',
    ],
    'GROUP_TREASURER': [
        'group:view_reports',
        'financial_reports:view',
        'contributions:view',
        'contributions:record_cash',
        'cash_payments:record',
        'payments:view',
        'payments:reconcile',
        'payments:match',
        'payments:flag_exception',
        'receipts:view',
        'receipts:issue',
        'payouts:view',
        'payouts:prepare',
        'payouts:request',
        'payouts:record_execution',
        'disputes:view_financial',
        'announcements:view',
        'group:approve_rules',
    ],
    'GROUP_MEMBER': [
        'group:approve_rules',
        'contributions:view',
        'announcements:view',
    ]
}


def ensure_permissions_seeded():
    """Idempotently seeds all standard permissions into the database."""
    for codename, name, category in DEFAULT_PERMISSIONS:
        PermissionCatalog.objects.get_or_create(
            codename=codename,
            defaults={'name': name, 'category': category}
        )

    # Ensure system roles exist as system-level templates (group=None)
    for role_code, perms in SYSTEM_ROLE_PERMISSIONS.items():
        role, _ = GroupRole.objects.get_or_create(
            group=None,
            code=role_code,
            defaults={
                'name': role_code.replace('_', ' ').title(),
                'is_system_role': True,
                'description': f"Default system role for {role_code}"
            }
        )
        catalog_items = PermissionCatalog.objects.filter(codename__in=perms)
        role.permissions.set(catalog_items)


def has_group_permission(user, group, permission_codename: str) -> bool:
    """
    Evaluates whether an authenticated user has a specific permission within the scope of a group.
    Validates user active status, account suspension, active membership, and role permissions.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False

    if getattr(user, 'account_status', None) == 'SUSPENDED':
        return False

    # Platform super admins can view/audit, but cannot casually bypass group financial operations
    if user.is_platform_admin and permission_codename in ['group:view_reports', 'contributions:view']:
        return True

    from apps.groups.models import GroupMembership
    try:
        membership = GroupMembership.objects.get(
            group=group,
            user=user,
            status=GroupMembership.MembershipStatus.ACTIVE
        )
    except GroupMembership.DoesNotExist:
        return False

    # Check permissions granted by any role assigned to this membership
    has_perm = MembershipRoleAssignment.objects.filter(
        membership=membership,
        role__permissions__codename=permission_codename
    ).exists()

    return has_perm


def get_user_group_permissions(user, group) -> set:
    """Returns the set of permission codenames that the user holds in a specific group."""
    if not user or not user.is_authenticated or not user.is_active:
        return set()

    if getattr(user, 'account_status', None) == 'SUSPENDED':
        return set()

    from apps.groups.models import GroupMembership
    try:
        membership = GroupMembership.objects.get(
            group=group,
            user=user,
            status=GroupMembership.MembershipStatus.ACTIVE
        )
    except GroupMembership.DoesNotExist:
        return set()

    return set(
        PermissionCatalog.objects.filter(
            roles__assignments__membership=membership
        ).values_list('codename', flat=True)
    )
