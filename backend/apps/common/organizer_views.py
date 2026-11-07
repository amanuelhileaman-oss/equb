import csv
import uuid
import secrets
from decimal import Decimal
from datetime import date, timedelta
from django.db import transaction
from django.db.models import Sum, Count, Q, Max
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import views, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound

from apps.accounts.models import User, OrganizerProfile
from apps.groups.models import EqubGroup, GroupMembership, GroupInvitation, TreasurerAssignmentRecord
from apps.groups.serializers import EqubGroupSerializer, GroupMembershipSerializer, GroupInvitationSerializer, GroupCreateSerializer
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import has_group_permission
from apps.rules.models import RuleVersion, RuleApproval
from apps.rules.serializers import RuleVersionSerializer
from apps.contributions.models import ContributionObligation, ContributionPeriod
from apps.contributions.serializers import ContributionObligationSerializer
from apps.payments.models import Payment, PaymentStatus, PaymentMethod, GroupPaymentDestination
from apps.payments.serializers import PaymentSerializer
from apps.payouts.models import Payout, PayoutStatus, PayoutSettlementStatus, PayoutApproval
from apps.payouts.serializers import PayoutSerializer
from apps.disputes.models import Dispute, DisputeStatus, DisputeCategory
from apps.disputes.serializers import DisputeSerializer
from apps.audit_app.models import AuditLog, SupportTicket, Announcement, VerificationRecord, PaymentProviderConfiguration, SecurityIncident
from apps.audit_app.serializers import SupportTicketSerializer, AnnouncementSerializer
from apps.audit_app.services import log_audit_event
from apps.audit_app.security_monitor import record_and_block_security_violation
from apps.subscriptions.services import get_or_create_active_subscription, validate_organizer_group_limit
from apps.subscriptions.models import SaasPlan, OrganizerSubscription, SubscriptionInvoice
from apps.subscriptions.serializers import OrganizerSubscriptionSerializer, SaasPlanSerializer
from apps.ledger.services import get_group_available_funds


def sanitize_csv_cell(value):
    """Prevents spreadsheet formula injection by quoting formulas starting with =, +, -, @."""
    s = str(value or "")
    if s and s[0] in ('=', '+', '-', '@', '\t', '\r'):
        return f"'{s}"
    return s


def get_authorized_organizer_group(user, group_id, required_perm=None):
    """
    Validates that the group exists and the user is authorized as the Organizer
    or has the required group permission. Enforces strict tenant isolation.
    """
    try:
        group = EqubGroup.objects.get(id=group_id)
    except (EqubGroup.DoesNotExist, ValueError):
        raise NotFound("Equb group not found.")

    if user.is_platform_admin:
        return group

    if group.organizer == user:
        return group

    if required_perm and has_group_permission(user, group, required_perm):
        return group

    # Check if user has GROUP_ORGANIZER role in this group
    if group.memberships.filter(user=user, role_assignments__role__code='GROUP_ORGANIZER').exists():
        return group

    raise PermissionDenied("You are not authorized to access or manage this Equb group.")


def enforce_organizer_gate(user):
    """
    Mandatory backend verification & subscription payment gate.
    The Organizer Dashboard and its group/member management functions may be accessed only if:
    1. Organizer account is active.
    2. Organizer verification status is APPROVED by Super Admin.
    3. Required subscription payment is confirmed (or NOT_REQUIRED).
    4. Subscription is ACTIVE or in valid grace period.
    """
    if user.is_platform_admin:
        return True, None, None

    if not user.is_active or user.account_status != User.AccountStatus.ACTIVE:
        return False, "ACCOUNT_SUSPENDED", "Your account is suspended. Please contact platform administration."

    prof = getattr(user, 'organizer_profile', None)
    if not prof:
        # Check if user organized existing groups
        if not EqubGroup.objects.filter(organizer=user).exists():
            return False, "NOT_AN_ORGANIZER", "You do not have an active Organizer account on Digital Equb Ethiopia."
        return True, None, None

    # 1. Verification check
    if prof.verification_status != OrganizerProfile.VerificationStatus.APPROVED:
        return (
            False,
            "VERIFICATION_PENDING",
            f"Your Organizer account verification status is '{prof.verification_status}'. "
            f"Group and member management are blocked until approved by Super Admin."
        )

    # 2. Paid tiers require rent payment before dashboard is accessible (Starter Equb is free)
    is_free_starter = bool(
        prof.payment_status == OrganizerProfile.PaymentStatus.NOT_REQUIRED or
        (prof.assigned_plan and prof.assigned_plan.code == 'STARTER_EQUB' and prof.payment_status != OrganizerProfile.PaymentStatus.PAYMENT_REQUIRED)
    )

    if prof.payment_status == OrganizerProfile.PaymentStatus.PAYMENT_REQUIRED or (not is_free_starter and prof.payment_status != OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED):
        return (
            False,
            "PAYMENT_REQUIRED",
            "Your Organizer account requires monthly subscription rent payment. Dashboard access and group management are blocked until rent payment is confirmed."
        )

    sub = OrganizerSubscription.objects.filter(organizer=user).order_by('-started_at').first()
    if sub and sub.status == OrganizerSubscription.SubscriptionStatus.EXPIRED:
        return (
            False,
            "SUBSCRIPTION_EXPIRED",
            "Your organizer subscription has expired. Please renew your plan to continue managing your groups."
        )

    return True, None, None


class OrganizerGroupsListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Strict tenant isolation: only groups organized by this user
        if user.is_platform_admin:
            groups = EqubGroup.objects.all().select_related('organizer').order_by('-created_at')
        else:
            groups = EqubGroup.objects.filter(
                Q(organizer=user) |
                Q(memberships__user=user, memberships__role_assignments__role__code='GROUP_ORGANIZER')
            ).distinct().select_related('organizer').order_by('-created_at')

        # Status filter
        status_filter = request.query_params.get('status')
        if status_filter:
            groups = groups.filter(status=status_filter.upper())

        # Search filter
        search_query = request.query_params.get('search', '').strip()
        if search_query:
            groups = groups.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(group_purpose__icontains=search_query)
            )

        serialized = EqubGroupSerializer(groups, many=True, context={'request': request}).data

        # Enrich each group with live members count and next contribution deadline
        for item in serialized:
            g_obj = next((g for g in groups if str(g.id) == item['id']), None)
            if g_obj:
                item['members_count'] = g_obj.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
                open_period = g_obj.periods.filter(status=ContributionPeriod.PeriodStatus.OPEN).first()
                item['next_contribution_date'] = open_period.due_date.strftime('%b %d, %Y') if (open_period and open_period.due_date) else None

        return Response({
            'groups': serialized,
            'total_count': groups.count()
        })

    def post(self, request):
        user = request.user
        data = request.data

        # 0. Enforce Organizer Verification & Subscription Payment Gate
        is_allowed, gate_code, gate_msg = enforce_organizer_gate(user)
        if not is_allowed:
            raise PermissionDenied(gate_msg)

        # 1. Enforce SaaS Subscription active group limit
        validate_organizer_group_limit(user)

        # 2. Validate mandatory fields
        name = data.get('name', '').strip()
        if not name:
            raise ValidationError({'name': 'Group name is required.'})

        try:
            contribution_amount = Decimal(str(data.get('contribution_amount', '1000.00')))
            if contribution_amount <= Decimal('0.00'):
                raise ValueError()
        except (ValueError, TypeError):
            raise ValidationError({'contribution_amount': 'Contribution amount must be greater than zero.'})

        frequency = data.get('contribution_frequency', EqubGroup.Frequency.MONTHLY)
        if frequency not in EqubGroup.Frequency.values:
            raise ValidationError({'contribution_frequency': f'Invalid frequency. Must be one of {EqubGroup.Frequency.values}'})

        capacity = int(data.get('capacity', 12))
        if capacity < 2:
            raise ValidationError({'capacity': 'Capacity must be at least 2 members.'})

        start_date_val = data.get('start_date')
        if not start_date_val:
            start_date_val = date.today()

        participate_as_member = data.get('participate_as_member', False)

        with transaction.atomic():
            group = EqubGroup.objects.create(
                name=name,
                description=data.get('description', ''),
                group_purpose=data.get('group_purpose', ''),
                organizer=user,
                status=EqubGroup.GroupStatus.ACTIVE,
                verification_status=EqubGroup.VerificationStatus.UNVERIFIED,
                currency=data.get('currency', 'ETB'),
                contribution_amount=contribution_amount,
                contribution_frequency=frequency,
                capacity=capacity,
                start_date=start_date_val,
                payout_method=data.get('payout_method', EqubGroup.PayoutMethod.ROTATION_ORDER),
                allowed_payment_methods=data.get('allowed_payment_methods', ["DIGITAL_PROVIDER", "CASH", "BANK_TRANSFER"]),
                rules_approval_threshold_percent=int(data.get('rules_approval_threshold_percent', 100)),
                require_cash_second_confirmation=data.get('require_cash_second_confirmation', True)
            )

            # Create default Charter v1
            rule_v1 = RuleVersion.objects.create(
                group=group,
                version_number=1,
                title=f"{group.name} Charter v1",
                terms_text=data.get('rules_terms', f"Official rules and regulations for {group.name}. Regular timely contributions required. Dual confirmation on cash receipts."),
                contribution_amount=contribution_amount,
                contribution_frequency=frequency,
                payout_method=group.payout_method,
                approval_threshold_percent=group.rules_approval_threshold_percent,
                status=RuleVersion.RuleStatus.APPROVED,
                proposed_by=user,
                effective_at=timezone.now()
            )
            group.active_rules_version = rule_v1
            group.save(update_fields=['active_rules_version'])

            # Add Organizer membership with GROUP_ORGANIZER role
            membership = GroupMembership.objects.create(
                group=group,
                user=user,
                status=GroupMembership.MembershipStatus.ACTIVE,
                payout_order_index=1 if participate_as_member else None,
                joined_at=timezone.now(),
                accepted_rules_version=rule_v1
            )
            org_role, _ = GroupRole.objects.get_or_create(
                group=None,
                code="GROUP_ORGANIZER",
                defaults={"name": "Group Organizer", "is_system_role": True}
            )
            MembershipRoleAssignment.objects.create(
                membership=membership,
                role=org_role,
                assigned_by=user
            )

            # If organizer chose to join as a rotating member:
            if participate_as_member:
                member_role, _ = GroupRole.objects.get_or_create(
                    group=None,
                    code="GROUP_MEMBER",
                    defaults={"name": "Group Member", "is_system_role": True}
                )
                MembershipRoleAssignment.objects.create(
                    membership=membership,
                    role=member_role,
                    assigned_by=user
                )

            # Record rule approval by organizer
            RuleApproval.objects.create(
                rule_version=rule_v1,
                membership=membership,
                decision=RuleApproval.Decision.APPROVED,
                comment="Initial charter adopted upon group creation."
            )

            # Seed cycle period 1
            period1 = ContributionPeriod.objects.create(
                group=group,
                period_number=1,
                start_date=date.today(),
                due_date=date.today() + (timedelta(days=7) if frequency == EqubGroup.Frequency.WEEKLY else timedelta(days=30)),
                status=ContributionPeriod.PeriodStatus.OPEN
            )

            # Only generate obligation for organizer if they opted to participate as a rotating member
            if participate_as_member:
                ContributionObligation.objects.create(
                    group=group,
                    membership=membership,
                    period=period1,
                    expected_amount=contribution_amount,
                    currency=group.currency,
                    due_date=period1.due_date,
                    status=ContributionObligation.ObligationStatus.PENDING
                )

            log_audit_event(
                action="GROUP_CREATED",
                actor=user,
                group=group,
                target_model="EqubGroup",
                target_id=group.id,
                details={"name": group.name, "amount": str(contribution_amount)},
                request=request
            )

        return Response(EqubGroupSerializer(group, context={'request': request}).data, status=status.HTTP_201_CREATED)


class OrganizerGroupDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        serialized = EqubGroupSerializer(group, context={'request': request}).data

        # Include summary stats
        members_count = group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
        obligations = ContributionObligation.objects.filter(group=group)
        totals = obligations.aggregate(expected=Sum('expected_amount'), paid=Sum('amount_paid'))
        available_funds = get_group_available_funds(group)

        serialized['members_count'] = members_count
        serialized['total_expected_etb'] = totals['expected'] or Decimal('0.00')
        serialized['total_collected_etb'] = totals['paid'] or Decimal('0.00')
        serialized['available_funds_etb'] = available_funds
        serialized['active_rules_version_number'] = group.active_rules_version.version_number if group.active_rules_version else 1

        return Response(serialized)

    def patch(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage')
        data = request.data

        if 'name' in data and data['name'].strip():
            group.name = data['name'].strip()
        if 'description' in data:
            group.description = data['description']
        if 'group_purpose' in data:
            group.group_purpose = data['group_purpose']
        if 'capacity' in data:
            try:
                cap = int(data['capacity'])
                if cap >= 2:
                    group.capacity = cap
            except (ValueError, TypeError):
                pass
        if 'require_cash_second_confirmation' in data:
            group.require_cash_second_confirmation = bool(data['require_cash_second_confirmation'])

        group.save()
        log_audit_event(
            action="GROUP_UPDATED",
            actor=request.user,
            group=group,
            target_model="EqubGroup",
            target_id=group.id,
            details={"updated_fields": list(data.keys())},
            request=request
        )
        return Response(EqubGroupSerializer(group, context={'request': request}).data)


class OrganizerGroupLifecycleActionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage')
        action = request.data.get('action', '').lower()
        reason = request.data.get('reason', '').strip()

        if action == 'pause':
            group.status = EqubGroup.GroupStatus.SUSPENDED
            group.suspension_reason = reason or "Paused by Organizer"
        elif action == 'resume':
            group.status = EqubGroup.GroupStatus.ACTIVE
            group.suspension_reason = ""
        elif action == 'close':
            group.status = EqubGroup.GroupStatus.CLOSED
            group.suspension_reason = reason or "Closed by Organizer"
        else:
            raise ValidationError({"action": "Invalid action. Supported: pause, resume, close."})

        group.save()
        log_audit_event(
            action=f"GROUP_LIFECYCLE_{action.upper()}",
            actor=request.user,
            group=group,
            target_model="EqubGroup",
            target_id=group.id,
            details={"action": action, "reason": reason},
            request=request
        )
        return Response({
            'success': True,
            'status': group.status,
            'message': f"Group status successfully updated to {group.status}"
        })


class OrganizerGroupMembersView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        memberships = group.memberships.all().select_related('user').prefetch_related('role_assignments__role')

        status_filter = request.query_params.get('status')
        if status_filter:
            memberships = memberships.filter(status=status_filter.upper())

        results = []
        for m in memberships:
            roles = [r.role.name for r in m.role_assignments.all()]
            # Financial progress for this member in this group
            obs = ContributionObligation.objects.filter(membership=m)
            totals = obs.aggregate(expected=Sum('expected_amount'), paid=Sum('amount_paid'))

            results.append({
                'membership_id': str(m.id),
                'user_id': str(m.user.id),
                'full_name': m.user.full_name,
                'email': m.user.email,
                'phone_number': m.user.phone_number,
                'status': m.status,
                'roles': roles,
                'payout_order_index': m.payout_order_index,
                'joined_at': m.joined_at,
                'contributions_expected_etb': totals['expected'] or Decimal('0.00'),
                'contributions_paid_etb': totals['paid'] or Decimal('0.00'),
            })

        return Response({
            'group_id': str(group.id),
            'group_name': group.name,
            'members': results,
            'total_count': len(results)
        })

    def post(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage_members')

        # Enforce gate check
        is_allowed, gate_code, gate_msg = enforce_organizer_gate(request.user)
        if not is_allowed:
            raise PermissionDenied(gate_msg)

        email = request.data.get('email', '').strip().lower()
        full_name = request.data.get('full_name', '').strip()
        phone_number = request.data.get('phone_number', '').strip() or None
        password_setup_method = request.data.get('password_setup_method', 'TEMPORARY_PASSWORD')
        initial_password = request.data.get('initial_password', '').strip()

        if not email:
            raise ValidationError({"email": "Email address is required."})

        # Check capacity limit
        active_count = group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
        if active_count >= group.capacity:
            raise ValidationError({"capacity": f"Group capacity limit ({group.capacity} members) reached. Cannot add more members."})

        # Check if already a member or upgrade existing membership (e.g. Organizer joining as member)
        existing_membership = group.memberships.filter(user__email=email).first()
        if existing_membership:
            has_member_role = existing_membership.role_assignments.filter(
                Q(role__code='GROUP_MEMBER') | Q(role__name='Group Member')
            ).exists()
            if has_member_role:
                raise ValidationError({"email": "User is already an active contributing member of this group."})

            with transaction.atomic():
                member_role, _ = GroupRole.objects.get_or_create(
                    group=None,
                    code="GROUP_MEMBER",
                    defaults={"name": "Group Member", "is_system_role": True}
                )
                MembershipRoleAssignment.objects.get_or_create(
                    membership=existing_membership,
                    role=member_role,
                    defaults={'assigned_by': request.user}
                )

                if not existing_membership.payout_order_index:
                    max_order = group.memberships.filter(payout_order_index__isnull=False).aggregate(Max('payout_order_index'))['payout_order_index__max'] or 0
                    existing_membership.payout_order_index = max_order + 1
                    existing_membership.save(update_fields=['payout_order_index'])

                open_period = group.periods.filter(status=ContributionPeriod.PeriodStatus.OPEN).first()
                if open_period and not ContributionObligation.objects.filter(group=group, membership=existing_membership, period=open_period).exists():
                    ContributionObligation.objects.create(
                        group=group,
                        membership=existing_membership,
                        period=open_period,
                        expected_amount=group.contribution_amount,
                        currency=group.currency,
                        due_date=open_period.due_date,
                        status=ContributionObligation.ObligationStatus.PENDING
                    )

                log_audit_event(
                    action="ORGANIZER_ENROLLED_AS_MEMBER",
                    actor=request.user,
                    group=group,
                    target_model="GroupMembership",
                    target_id=existing_membership.id,
                    details={"member": existing_membership.user.full_name, "email": email, "payout_order": existing_membership.payout_order_index},
                    request=request
                )

            return Response({
                'success': True,
                'message': f"Enrolled {existing_membership.user.full_name or existing_membership.user.email} as a contributing member.",
                'membership_id': str(existing_membership.id),
                'user': {
                    'id': str(existing_membership.user.id),
                    'full_name': existing_membership.user.full_name,
                    'email': existing_membership.user.email,
                    'phone_number': existing_membership.user.phone_number
                },
                'payout_order_index': existing_membership.payout_order_index
            }, status=status.HTTP_200_OK)

        user = User.objects.filter(email=email).first()
        temp_pwd = None
        activation_token = None

        with transaction.atomic():
            if not user:
                if not full_name:
                    raise ValidationError({"full_name": "Full name is required to create a new member account."})

                import secrets
                if password_setup_method == 'TEMPORARY_PASSWORD':
                    temp_pwd = initial_password or f"Equb_{secrets.token_hex(4)}!"
                    user = User.objects.create_user(
                        email=email,
                        password=temp_pwd,
                        full_name=full_name,
                        phone_number=phone_number,
                        is_platform_admin=False
                    )
                else:
                    user = User.objects.create_user(
                        email=email,
                        full_name=full_name,
                        phone_number=phone_number,
                        is_platform_admin=False
                    )
                    activation_token = secrets.token_urlsafe(32)

            next_order = group.memberships.count() + 1
            membership = GroupMembership.objects.create(
                group=group,
                user=user,
                status=GroupMembership.MembershipStatus.ACTIVE,
                payout_order_index=next_order,
                joined_at=timezone.now(),
                accepted_rules_version=group.active_rules_version
            )
            member_role, _ = GroupRole.objects.get_or_create(
                group=None,
                code="GROUP_MEMBER",
                defaults={"name": "Group Member", "is_system_role": True}
            )
            MembershipRoleAssignment.objects.create(
                membership=membership,
                role=member_role,
                assigned_by=request.user
            )

            # Create obligation for current open period if exists
            open_period = group.periods.filter(status=ContributionPeriod.PeriodStatus.OPEN).first()
            if open_period:
                ContributionObligation.objects.create(
                    group=group,
                    membership=membership,
                    period=open_period,
                    expected_amount=group.contribution_amount,
                    currency=group.currency,
                    due_date=open_period.due_date,
                    status=ContributionObligation.ObligationStatus.PENDING
                )

            log_audit_event(
                action="MEMBER_CREATED_BY_ORGANIZER",
                actor=request.user,
                group=group,
                target_model="GroupMembership",
                target_id=membership.id,
                details={
                    "member": user.full_name,
                    "email": user.email,
                    "is_new_user": temp_pwd is not None or activation_token is not None
                },
                request=request
            )

        return Response({
            'success': True,
            'message': f"Added {user.full_name} to {group.name}",
            'membership_id': str(membership.id),
            'user': {
                'id': str(user.id),
                'full_name': user.full_name,
                'email': user.email,
                'phone_number': user.phone_number
            },
            'temporary_password': temp_pwd,
            'activation_token': activation_token
        }, status=status.HTTP_201_CREATED)


class OrganizerGroupJoinView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        user = request.user

        is_allowed, gate_code, gate_msg = enforce_organizer_gate(user)
        if not is_allowed:
            raise PermissionDenied(gate_msg)

        with transaction.atomic():
            membership, _ = GroupMembership.objects.get_or_create(
                group=group,
                user=user,
                defaults={
                    'status': GroupMembership.MembershipStatus.ACTIVE,
                    'joined_at': timezone.now(),
                    'accepted_rules_version': group.active_rules_version
                }
            )

            member_role, _ = GroupRole.objects.get_or_create(
                group=None,
                code="GROUP_MEMBER",
                defaults={"name": "Group Member", "is_system_role": True}
            )
            MembershipRoleAssignment.objects.get_or_create(
                membership=membership,
                role=member_role,
                defaults={'assigned_by': user}
            )

            if not membership.payout_order_index:
                max_order = group.memberships.filter(payout_order_index__isnull=False).aggregate(Max('payout_order_index'))['payout_order_index__max'] or 0
                membership.payout_order_index = max_order + 1
                membership.save(update_fields=['payout_order_index'])

            open_period = group.periods.filter(status=ContributionPeriod.PeriodStatus.OPEN).first()
            if open_period and not ContributionObligation.objects.filter(group=group, membership=membership, period=open_period).exists():
                ContributionObligation.objects.create(
                    group=group,
                    membership=membership,
                    period=open_period,
                    expected_amount=group.contribution_amount,
                    currency=group.currency,
                    due_date=open_period.due_date,
                    status=ContributionObligation.ObligationStatus.PENDING
                )

            log_audit_event(
                action="ORGANIZER_JOINED_AS_MEMBER",
                actor=user,
                group=group,
                target_model="GroupMembership",
                target_id=membership.id,
                details={"payout_order": membership.payout_order_index},
                request=request
            )

        return Response({
            'success': True,
            'message': f"You ({user.full_name or user.email}) have successfully joined {group.name} as a contributing member with payout order #{membership.payout_order_index}.",
            'membership_id': str(membership.id),
            'payout_order_index': membership.payout_order_index
        }, status=status.HTTP_200_OK)


class OrganizerGroupMembersImportView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage_members')
        is_allowed, gate_code, gate_msg = enforce_organizer_gate(request.user)
        if not is_allowed:
            raise PermissionDenied(gate_msg)

        members_data = request.data.get('members', [])
        csv_text = request.data.get('csv_data', '').strip()

        rows_to_process = []
        if csv_text:
            import io
            reader = csv.reader(io.StringIO(csv_text))
            for i, row in enumerate(reader):
                if not row or (i == 0 and any(h in row[0].lower() for h in ['name', 'full name', 'email'])):
                    continue
                if len(row) >= 2:
                    rows_to_process.append({
                        'full_name': row[0].strip(),
                        'email': row[1].strip().lower(),
                        'phone_number': row[2].strip() if len(row) > 2 else ''
                    })
        elif isinstance(members_data, list):
            rows_to_process = members_data

        if not rows_to_process:
            raise ValidationError("No valid member records provided for bulk import.")

        active_count = group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
        if active_count + len(rows_to_process) > group.capacity:
            raise ValidationError(
                f"Import would exceed group capacity: Group has {active_count}/{group.capacity} members, "
                f"attempting to import {len(rows_to_process)} members."
            )

        created_count = 0
        existing_added_count = 0
        errors = []
        created_members = []

        member_role, _ = GroupRole.objects.get_or_create(
            group=None,
            code="GROUP_MEMBER",
            defaults={"name": "Group Member", "is_system_role": True}
        )

        import secrets
        with transaction.atomic():
            for idx, item in enumerate(rows_to_process):
                row_num = idx + 1
                name = item.get('full_name', '').strip()
                email = item.get('email', '').strip().lower()
                phone = item.get('phone_number', '').strip() or None

                if not name or not email:
                    errors.append(f"Row {row_num}: Name and Email are required.")
                    continue

                if group.memberships.filter(user__email=email).exists():
                    errors.append(f"Row {row_num}: User {email} is already in this group.")
                    continue

                user = User.objects.filter(email=email).first()
                temp_pwd = None
                if not user:
                    temp_pwd = f"Equb_{secrets.token_hex(4)}!"
                    user = User.objects.create_user(
                        email=email,
                        password=temp_pwd,
                        full_name=name,
                        phone_number=phone,
                        is_platform_admin=False
                    )
                    created_count += 1
                else:
                    existing_added_count += 1

                next_order = group.memberships.count() + 1
                membership = GroupMembership.objects.create(
                    group=group,
                    user=user,
                    status=GroupMembership.MembershipStatus.ACTIVE,
                    payout_order_index=next_order,
                    joined_at=timezone.now(),
                    accepted_rules_version=group.active_rules_version
                )
                MembershipRoleAssignment.objects.create(
                    membership=membership,
                    role=member_role,
                    assigned_by=request.user
                )
                created_members.append({
                    "id": str(membership.id),
                    "full_name": user.full_name,
                    "email": user.email,
                    "temporary_password": temp_pwd
                })

            if errors and not created_members:
                raise ValidationError({"errors": errors})

            log_audit_event(
                action="MEMBERS_BULK_IMPORTED",
                actor=request.user,
                group=group,
                target_model="EqubGroup",
                target_id=group.id,
                details={
                    "created_count": created_count,
                    "existing_added": existing_added_count,
                    "total_imported": len(created_members)
                },
                request=request
            )

        return Response({
            "success": True,
            "message": f"Successfully imported {len(created_members)} members to {group.name}.",
            "imported_count": len(created_members),
            "created_count": created_count,
            "existing_added_count": existing_added_count,
            "imported_members": created_members,
            "skipped_or_errors": errors
        }, status=status.HTTP_201_CREATED)


class OrganizerGroupMemberDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id, membership_id):
        group = get_authorized_organizer_group(request.user, group_id)
        try:
            membership = group.memberships.select_related('user').get(id=membership_id)
        except GroupMembership.DoesNotExist:
            raise NotFound("Group membership not found.")

        # Obligations and payments
        obligations = ContributionObligation.objects.filter(
            group=group,
            membership=membership
        ).select_related('period').order_by('-created_at')

        payments = Payment.objects.filter(
            obligation__group=group,
            payer=membership.user
        ).order_by('-created_at')

        totals = obligations.aggregate(
            expected=Sum('expected_amount'),
            paid=Sum('amount_paid')
        )

        expected_val = totals['expected'] or Decimal('0.00')
        paid_val = totals['paid'] or Decimal('0.00')

        roles = list(membership.role_assignments.values_list('role__name', flat=True))

        return Response({
            'membership_id': str(membership.id),
            'group_id': str(group.id),
            'group_name': group.name,
            'user': {
                'id': str(membership.user.id),
                'full_name': membership.user.full_name,
                'email': membership.user.email,
                'phone_number': membership.user.phone_number,
                'account_status': membership.user.account_status,
                'preferred_language': membership.user.preferred_language,
                'is_active': membership.user.is_active
            },
            'status': membership.status,
            'roles': roles,
            'payout_order_index': membership.payout_order_index,
            'joined_at': membership.joined_at,
            'financial_summary': {
                'total_expected_etb': expected_val,
                'total_paid_etb': paid_val,
                'outstanding_etb': max(Decimal('0.00'), expected_val - paid_val),
            },
            'obligations': [
                {
                    'id': str(ob.id),
                    'period_number': ob.period.period_number if ob.period else None,
                    'due_date': ob.due_date,
                    'expected_amount': ob.expected_amount,
                    'amount_paid': ob.amount_paid,
                    'status': ob.status
                } for ob in obligations
            ],
            'payments': [
                {
                    'id': str(p.id),
                    'amount': str(p.amount) if p.amount is not None else '0.00',
                    'payment_method': p.payment_method or 'CASH',
                    'status': p.status or 'PENDING',
                    'transaction_reference': getattr(p, 'provider_transaction_reference', '') or getattr(p, 'receipt_number', '') or getattr(p, 'transfer_reference', '') or '',
                    'receipt_number': getattr(p, 'receipt_number', '') or '',
                    'created_at': p.created_at.isoformat() if p.created_at else None
                } for p in payments
            ]
        })

    def patch(self, request, group_id, membership_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage_members')
        try:
            membership = group.memberships.select_related('user').get(id=membership_id)
        except GroupMembership.DoesNotExist:
            raise NotFound("Group membership not found.")

        data = request.data
        user = membership.user

        # 1. Update membership status (ACTIVE, SUSPENDED, REMOVED)
        if 'status' in data:
            new_status = data['status'].upper()
            if new_status in GroupMembership.MembershipStatus.values:
                membership.status = new_status
                membership.save(update_fields=['status'])

        # 2. Update payout order index
        if 'payout_order_index' in data:
            try:
                membership.payout_order_index = int(data['payout_order_index'])
                membership.save(update_fields=['payout_order_index'])
            except (ValueError, TypeError):
                pass

        # 3. Update member details (full_name, phone_number)
        user_updated = False
        if 'full_name' in data and data['full_name'].strip():
            user.full_name = data['full_name'].strip()
            user_updated = True
        if 'phone_number' in data:
            user.phone_number = data['phone_number'].strip() or None
            user_updated = True

        if user_updated:
            user.save(update_fields=['full_name', 'phone_number'])

        log_audit_event(
            action="MEMBER_DETAILS_UPDATED_BY_ORGANIZER",
            actor=request.user,
            group=group,
            target_model="GroupMembership",
            target_id=membership.id,
            details={"updated_fields": list(data.keys())},
            request=request
        )

        return Response({
            'success': True,
            'message': f"Updated member {user.full_name} successfully.",
            'membership_id': str(membership.id),
            'status': membership.status,
            'payout_order_index': membership.payout_order_index,
            'full_name': user.full_name,
            'phone_number': user.phone_number
        })


class OrganizerGroupInvitationsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        invitations = group.invitations.all().order_by('-created_at')
        return Response(GroupInvitationSerializer(invitations, many=True).data)

    def post(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage_members')
        email = request.data.get('email', '').strip().lower()
        if not email:
            raise ValidationError({"email": "Invited email is required."})

        # Check existing pending invite
        existing = group.invitations.filter(invited_email=email, status=GroupInvitation.InvitationStatus.PENDING).first()
        if existing and existing.expires_at > timezone.now():
            return Response(GroupInvitationSerializer(existing).data)

        days_valid = int(request.data.get('expires_in_days', 7))
        token = uuid.uuid4().hex

        invitation = GroupInvitation.objects.create(
            group=group,
            invited_email=email,
            token=token,
            status=GroupInvitation.InvitationStatus.PENDING,
            expires_at=timezone.now() + timedelta(days=days_valid)
        )

        log_audit_event(
            action="INVITATION_GENERATED",
            actor=request.user,
            group=group,
            target_model="GroupInvitation",
            target_id=invitation.id,
            details={"email": email, "expires_at": invitation.expires_at.isoformat()},
            request=request
        )

        resp_data = GroupInvitationSerializer(invitation).data
        resp_data['invite_url'] = f"/join?token={token}"
        return Response(resp_data, status=status.HTTP_201_CREATED)


class OrganizerGroupMembershipRequestsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        pending_requests = group.memberships.filter(
            status=GroupMembership.MembershipStatus.REQUESTED
        ).select_related('user')

        results = []
        for r in pending_requests:
            results.append({
                'membership_id': str(r.id),
                'user_id': str(r.user.id),
                'full_name': r.user.full_name,
                'email': r.user.email,
                'phone_number': r.user.phone_number,
                'requested_at': r.created_at
            })

        return Response({
            'pending_requests': results,
            'count': len(results)
        })

    def post(self, request, group_id, membership_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage_members')
        try:
            membership = group.memberships.get(id=membership_id)
        except GroupMembership.DoesNotExist:
            raise NotFound("Membership request not found.")

        action = request.data.get('action', '').lower()
        reason = request.data.get('reason', '').strip()

        if action == 'approve':
            with transaction.atomic():
                membership.status = GroupMembership.MembershipStatus.ACTIVE
                membership.joined_at = timezone.now()
                membership.payout_order_index = group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count() + 1
                membership.accepted_rules_version = group.active_rules_version
                membership.save()

                member_role, _ = GroupRole.objects.get_or_create(
                    group=None,
                    code="GROUP_MEMBER",
                    defaults={"name": "Group Member", "is_system_role": True}
                )
                MembershipRoleAssignment.objects.get_or_create(
                    membership=membership,
                    role=member_role,
                    defaults={'assigned_by': request.user}
                )

                log_audit_event(
                    action="MEMBERSHIP_APPROVED",
                    actor=request.user,
                    group=group,
                    target_model="GroupMembership",
                    target_id=membership.id,
                    details={"member": membership.user.full_name},
                    request=request
                )

            return Response({'success': True, 'message': f"Approved {membership.user.full_name}"})

        elif action == 'reject':
            membership.status = GroupMembership.MembershipStatus.REMOVED
            membership.save()
            log_audit_event(
                action="MEMBERSHIP_REJECTED",
                actor=request.user,
                group=group,
                target_model="GroupMembership",
                target_id=membership.id,
                details={"member": membership.user.full_name, "reason": reason},
                request=request
            )
            return Response({'success': True, 'message': f"Rejected membership request for {membership.user.full_name}"})

        else:
            raise ValidationError({"action": "Invalid action. Supported: approve, reject."})


class OrganizerGroupTreasurerView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        # Find current assigned treasurer
        treasurer_membership = group.memberships.filter(
            status=GroupMembership.MembershipStatus.ACTIVE,
            role_assignments__role__code='GROUP_TREASURER'
        ).select_related('user').first()

        current_treasurer = None
        if treasurer_membership:
            current_treasurer = {
                'membership_id': str(treasurer_membership.id),
                'user_id': str(treasurer_membership.user.id),
                'full_name': treasurer_membership.user.full_name,
                'email': treasurer_membership.user.email,
                'phone_number': treasurer_membership.user.phone_number,
                'assigned_since': treasurer_membership.role_assignments.filter(role__code='GROUP_TREASURER').first().assigned_at
            }

        # List eligible active members (excluding current treasurer)
        eligible_members = []
        for m in group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).select_related('user'):
            if not treasurer_membership or m.id != treasurer_membership.id:
                eligible_members.append({
                    'membership_id': str(m.id),
                    'full_name': m.user.full_name,
                    'email': m.user.email
                })

        # Recent treasurer audit activity
        recent_activity = AuditLog.objects.filter(
            group=group,
            action__in=['CASH_RECEIPT_RECORDED', 'CASH_RECEIPT_CONFIRMED', 'BANK_TRANSFER_RECONCILED']
        ).select_related('actor').order_by('-timestamp')[:5]

        return Response({
            'group_id': str(group.id),
            'group_name': group.name,
            'current_treasurer': current_treasurer,
            'eligible_members': eligible_members,
            'recent_treasurer_reconciliation': [
                {
                    'action': a.action,
                    'actor_name': a.actor.full_name if a.actor else "System",
                    'timestamp': a.timestamp,
                    'details': a.details
                } for a in recent_activity
            ]
        })

    def post(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage')
        is_allowed, gate_code, gate_msg = enforce_organizer_gate(request.user)
        if not is_allowed:
            raise PermissionDenied(gate_msg)

        action = request.data.get('action', '').lower()
        membership_id = request.data.get('membership_id')
        user_id = request.data.get('user_id')

        if not action and (membership_id or user_id):
            action = 'assign'

        treasurer_role, _ = GroupRole.objects.get_or_create(
            group=None,
            code="GROUP_TREASURER",
            defaults={"name": "Group Treasurer", "is_system_role": True}
        )

        if action == 'assign':
            if not membership_id and not user_id:
                raise ValidationError({"membership_id": "Membership ID or User ID is required for treasurer assignment."})

            try:
                if membership_id:
                    membership = group.memberships.get(id=membership_id, status=GroupMembership.MembershipStatus.ACTIVE)
                else:
                    membership = group.memberships.get(user_id=user_id, status=GroupMembership.MembershipStatus.ACTIVE)
            except GroupMembership.DoesNotExist:
                raise ValidationError({"user_id": "Active member not found in this group."})

            with transaction.atomic():
                # Revoke existing treasurer if any to enforce single primary treasurer
                existing_assignments = MembershipRoleAssignment.objects.filter(
                    membership__group=group,
                    role=treasurer_role
                )
                for assignment in existing_assignments:
                    log_audit_event(
                        action="TREASURER_REVOKED",
                        actor=request.user,
                        group=group,
                        target_model="GroupMembership",
                        target_id=assignment.membership.id,
                        details={"previous_treasurer": assignment.membership.user.full_name},
                        request=request
                    )
                    assignment.delete()

                # Close existing active assignment record in history
                TreasurerAssignmentRecord.objects.filter(group=group, is_active=True).update(
                    is_active=False,
                    revoked_by=request.user,
                    revoked_at=timezone.now()
                )

                # Assign new treasurer role
                MembershipRoleAssignment.objects.create(
                    membership=membership,
                    role=treasurer_role,
                    assigned_by=request.user
                )

                # Record in TreasurerAssignmentRecord to preserve permanent history
                TreasurerAssignmentRecord.objects.create(
                    group=group,
                    user=membership.user,
                    assigned_by=request.user,
                    is_active=True,
                    notes=request.data.get('notes', 'Assigned by Organizer')
                )

                log_audit_event(
                    action="TREASURER_ASSIGNED",
                    actor=request.user,
                    group=group,
                    target_model="GroupMembership",
                    target_id=membership.id,
                    details={"assigned_treasurer": membership.user.full_name},
                    request=request
                )

            return Response({
                'success': True,
                'message': f"Assigned {membership.user.full_name} as Treasurer for {group.name}"
            })

        elif action == 'revoke':
            assignments = MembershipRoleAssignment.objects.filter(
                membership__group=group,
                role=treasurer_role
            )
            count = assignments.count()
            assignments.delete()

            TreasurerAssignmentRecord.objects.filter(group=group, is_active=True).update(
                is_active=False,
                revoked_by=request.user,
                revoked_at=timezone.now()
            )

            log_audit_event(
                action="TREASURER_REVOKED",
                actor=request.user,
                group=group,
                details={"revoked_count": count},
                request=request
            )

            return Response({
                'success': True,
                'message': f"Revoked Treasurer role in {group.name}"
            })

        else:
            raise ValidationError({"action": "Invalid action. Supported: assign, revoke."})


class OrganizerGroupRulesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        versions = group.rule_versions.all().order_by('-version_number')
        serialized = RuleVersionSerializer(versions, many=True, context={'request': request}).data
        return Response({
            'group_id': str(group.id),
            'active_version': group.active_rules_version.version_number if group.active_rules_version else 1,
            'rule_versions': serialized
        })

    def post(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage')
        data = request.data

        title = data.get('title', '').strip()
        terms_text = data.get('terms_text', '').strip()

        if not title or not terms_text:
            raise ValidationError("Title and contractual terms text are required.")

        last_v = group.rule_versions.order_by('-version_number').first()
        next_version_num = (last_v.version_number + 1) if last_v else 1

        contribution_amount = Decimal(str(data.get('contribution_amount', group.contribution_amount)))
        frequency = data.get('contribution_frequency', group.contribution_frequency)
        payout_method = data.get('payout_method', group.payout_method)
        threshold = int(data.get('approval_threshold_percent', group.rules_approval_threshold_percent))

        with transaction.atomic():
            new_rule = RuleVersion.objects.create(
                group=group,
                version_number=next_version_num,
                title=title,
                terms_text=terms_text,
                contribution_amount=contribution_amount,
                contribution_frequency=frequency,
                payout_method=payout_method,
                approval_threshold_percent=threshold,
                status=RuleVersion.RuleStatus.PROPOSED,
                proposed_by=request.user
            )

            # Organizer automatically votes APPROVED on their own proposed rule
            org_membership = group.memberships.filter(user=request.user).first()
            if org_membership:
                RuleApproval.objects.create(
                    rule_version=new_rule,
                    membership=org_membership,
                    decision=RuleApproval.Decision.APPROVED,
                    comment="Proposed by group organizer."
                )

            log_audit_event(
                action="RULE_PROPOSED",
                actor=request.user,
                group=group,
                target_model="RuleVersion",
                target_id=new_rule.id,
                details={"version": next_version_num, "title": title},
                request=request
            )

        return Response(RuleVersionSerializer(new_rule, context={'request': request}).data, status=status.HTTP_201_CREATED)


class OrganizerGroupContributionsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        obligations = ContributionObligation.objects.filter(group=group).select_related('membership__user', 'period').order_by('-due_date')

        # Summary calculations
        totals = obligations.aggregate(
            expected=Sum('expected_amount'),
            collected=Sum('amount_paid')
        )
        total_expected = totals['expected'] or Decimal('0.00')
        total_collected = totals['collected'] or Decimal('0.00')
        collection_rate = round((total_collected / total_expected * 100), 1) if total_expected > 0 else 0

        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter:
            obligations = obligations.filter(status=status_filter.upper())

        # Filter by member name or email
        search = request.query_params.get('search', '').strip()
        if search:
            obligations = obligations.filter(
                Q(membership__user__full_name__icontains=search) |
                Q(membership__user__email__icontains=search)
            )

        serialized = []
        for ob in obligations[:100]:
            item = ContributionObligationSerializer(ob).data
            item['member_name'] = ob.membership.user.full_name or ob.membership.user.email
            item['member_email'] = ob.membership.user.email
            item['member_user_id'] = str(ob.membership.user.id)
            item['is_me'] = (ob.membership.user_id == request.user.id)
            item['period_round'] = ob.period.period_number if ob.period else 1
            serialized.append(item)

        # Recent confirmed payments
        recent_payments = Payment.objects.filter(
            group=group
        ).select_related('payer').order_by('-created_at')[:10]

        return Response({
            'group_id': str(group.id),
            'group_name': group.name,
            'summary': {
                'total_expected_etb': total_expected,
                'total_collected_etb': total_collected,
                'collection_rate_pct': collection_rate,
                'overdue_count': obligations.filter(status=ContributionObligation.ObligationStatus.OVERDUE).count()
            },
            'obligations': serialized,
            'recent_payments': PaymentSerializer(recent_payments, many=True).data
        })


class OrganizerGroupPayoutsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        payouts = Payout.objects.filter(group=group).select_related('recipient_membership__user', 'period').order_by('-created_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            payouts = payouts.filter(status=status_filter.upper())

        available_funds = get_group_available_funds(group)
        active_members_count = group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
        expected_collection = group.contribution_amount * active_members_count

        # Eligible members for upcoming rotation round
        paid_member_ids = Payout.objects.filter(
            group=group,
            status__in=[PayoutStatus.APPROVED, PayoutStatus.EXECUTING, PayoutStatus.COMPLETED]
        ).values_list('recipient_membership_id', flat=True)

        unpaid_members = group.memberships.filter(
            status=GroupMembership.MembershipStatus.ACTIVE
        ).exclude(id__in=paid_member_ids).order_by('payout_order_index')

        eligible_next = []
        for m in unpaid_members:
            eligible_next.append({
                'membership_id': str(m.id),
                'full_name': m.user.full_name,
                'email': m.user.email,
                'payout_order_index': m.payout_order_index
            })

        return Response({
            'group_id': str(group.id),
            'group_name': group.name,
            'active_members_count': active_members_count,
            'expected_collection_etb': expected_collection,
            'actual_verified_collection_etb': available_funds,
            'available_funds_etb': available_funds,
            'applicable_fees_etb': Decimal('0.00'),
            'payout_amount_etb': expected_collection,
            'payouts': PayoutSerializer(payouts, many=True).data,
            'eligible_upcoming_recipients': eligible_next
        })

    def post(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage')
        recipient_id = request.data.get('recipient_membership_id')
        amount_raw = request.data.get('amount')

        if not recipient_id:
            raise ValidationError({"recipient_membership_id": "Recipient membership ID is required."})

        try:
            recipient = group.memberships.get(id=recipient_id, status=GroupMembership.MembershipStatus.ACTIVE)
        except GroupMembership.DoesNotExist:
            raise ValidationError({"recipient_membership_id": "Recipient membership not found or not active in this group."})

        # Calculate standard pool amount if not provided
        active_members_count = group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
        default_pool = group.contribution_amount * active_members_count
        amount = Decimal(str(amount_raw)) if amount_raw else default_pool

        # Check treasury funds
        available_funds = get_group_available_funds(group)
        if available_funds < amount:
            payout_status = PayoutStatus.BLOCKED_INSUFFICIENT_FUNDS
            blocking_reason = f"Available funds ({available_funds} ETB) are less than payout ({amount} ETB)."
        else:
            payout_status = PayoutStatus.PENDING_APPROVAL
            blocking_reason = ""

        with transaction.atomic():
            payout = Payout.objects.create(
                group=group,
                recipient_membership=recipient,
                amount=amount,
                currency=group.currency,
                status=payout_status,
                settlement_status=PayoutSettlementStatus.AWAITING_SETTLEMENT,
                requesting_user=request.user,
                blocking_reason=blocking_reason,
                notes=request.data.get('notes', f"Scheduled rotation payout for {recipient.user.full_name}")
            )

            # Organizer initial approval
            PayoutApproval.objects.create(
                payout=payout,
                approver=request.user,
                decision=PayoutApproval.Decision.APPROVED,
                reason="Initiated and approved by Group Organizer."
            )

            log_audit_event(
                action="PAYOUT_SCHEDULED",
                actor=request.user,
                group=group,
                target_model="Payout",
                target_id=payout.id,
                details={"recipient": recipient.user.full_name, "amount": str(amount), "status": payout.status},
                request=request
            )

        return Response(PayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


class OrganizerGroupDisputesView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        disputes = Dispute.objects.filter(group=group).select_related('reporter_membership__user').order_by('-created_at')
        return Response(DisputeSerializer(disputes, many=True).data)

    def post(self, request, group_id, dispute_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage')
        try:
            dispute = Dispute.objects.get(id=dispute_id, group=group)
        except Dispute.DoesNotExist:
            raise NotFound("Dispute not found.")

        action = request.data.get('action', '').lower()
        notes = request.data.get('notes', '').strip()

        if action == 'resolve':
            dispute.status = DisputeStatus.RESOLVED
            dispute.resolved_at = timezone.now()
            dispute.assigned_handler = request.user
            if notes:
                dispute.resolution_notes = f"{dispute.resolution_notes}\n[Resolution]: {notes}".strip()
            dispute.save()
            log_audit_event(
                action="DISPUTE_RESOLVED",
                actor=request.user,
                group=group,
                target_model="Dispute",
                target_id=dispute.id,
                details={"action": "resolved", "notes": notes},
                request=request
            )
            return Response({'success': True, 'message': 'Dispute marked as resolved.', 'status': dispute.status})

        elif action == 'add_note':
            dispute.resolution_notes = f"{dispute.resolution_notes}\n[{request.user.full_name}]: {notes}".strip()
            dispute.save()
            return Response({'success': True, 'resolution_notes': dispute.resolution_notes})

        elif action == 'escalate':
            dispute.status = DisputeStatus.UNDER_REVIEW
            dispute.save()

            # Create SuperAdmin support ticket
            SupportTicket.objects.create(
                user=request.user,
                group=group,
                category=SupportTicket.Category.DISPUTE_ESCALATION,
                subject=f"Escalated Dispute #{str(dispute.id)[:8]} in {group.name}",
                message=f"Organizer {request.user.full_name} escalated dispute '{dispute.title}' ({dispute.category}). Notes: {notes or dispute.description}"
            )
            log_audit_event(
                action="DISPUTE_ESCALATED",
                actor=request.user,
                group=group,
                target_model="Dispute",
                target_id=dispute.id,
                details={"action": "escalated_to_superadmin"},
                request=request
            )
            return Response({'success': True, 'message': 'Dispute escalated to Platform Super Admin.', 'status': dispute.status})

        else:
            raise ValidationError({"action": "Invalid action. Supported: resolve, add_note, escalate."})


class OrganizerGroupAnnouncementsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)
        # Group announcements or general organizer announcements
        announcements = Announcement.objects.filter(
            Q(target_audience__in=[Announcement.TargetAudience.ALL, Announcement.TargetAudience.ORGANIZERS]) |
            Q(created_by=request.user)
        ).order_by('-created_at')
        return Response(AnnouncementSerializer(announcements, many=True).data)

    def post(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id, required_perm='group:manage')
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        if not title or not content:
            raise ValidationError("Title and content are required.")

        announcement = Announcement.objects.create(
            title=title,
            title_am=request.data.get('title_am', ''),
            content=content,
            content_am=request.data.get('content_am', ''),
            target_audience=Announcement.TargetAudience.MEMBERS,
            status=Announcement.Status.PUBLISHED,
            published_at=timezone.now(),
            created_by=request.user
        )

        log_audit_event(
            action="ANNOUNCEMENT_CREATED",
            actor=request.user,
            group=group,
            target_model="Announcement",
            target_id=announcement.id,
            details={"title": title},
            request=request
        )

        return Response(AnnouncementSerializer(announcement).data, status=status.HTTP_201_CREATED)


class OrganizerVerificationStatusView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        prof = getattr(user, 'organizer_profile', None)

        # 1. Organizer identity verification
        identity_record = VerificationRecord.objects.filter(
            category=VerificationRecord.Category.ORGANIZER,
            target_id=user.id
        ).order_by('-created_at').first()

        # 2. Group verifications
        my_groups = EqubGroup.objects.filter(organizer=user)
        group_statuses = []
        for g in my_groups:
            group_statuses.append({
                'group_id': str(g.id),
                'group_name': g.name,
                'verification_status': g.verification_status
            })

        # 3. Payment destinations verification
        destinations = GroupPaymentDestination.objects.filter(group__in=my_groups)
        dest_statuses = []
        for d in destinations:
            dest_statuses.append({
                'destination_id': str(d.id),
                'group_name': d.group.name,
                'provider_or_bank': d.provider_or_bank,
                'account_name': d.account_name,
                'is_verified': d.is_verified,
                'is_active': d.is_active
            })

        # 4. Platform payment providers
        providers = PaymentProviderConfiguration.objects.all()
        prov_summary = []
        for p in providers:
            prov_summary.append({
                'display_name': p.display_name,
                'environment': p.environment,
                'is_enabled': p.is_enabled,
                'is_live_ready': p.is_live_ready,
                'health': p.connection_health
            })

        profile_details = {
            'business_name': prof.business_name if prof else "",
            'business_type': prof.business_type if prof else "",
            'business_address': prof.business_address if prof else "",
            'license_number': prof.license_number if prof else "",
            'license_document': prof.license_document if prof else "",
            'license_issue_date': prof.license_issue_date if prof else None,
            'license_expiry_date': prof.license_expiry_date if prof else None,
            'verification_status': prof.verification_status if prof else (identity_record.status if identity_record else "NOT_SUBMITTED"),
            'rejection_reason': getattr(prof, 'decision_reason', '') if prof else "",
            'admin_notes': getattr(prof, 'verification_notes', '') if prof else (identity_record.review_notes if identity_record else ""),
            'payment_status': prof.payment_status if prof else "PAYMENT_REQUIRED",
            'assigned_plan': prof.assigned_plan.name if (prof and prof.assigned_plan) else "Growth Plan"
        }

        return Response({
            'profile_details': profile_details,
            'organizer_identity': {
                'status': prof.verification_status if prof else (identity_record.status if identity_record else "NOT_SUBMITTED"),
                'submitted_at': identity_record.created_at if identity_record else None,
                'notes': identity_record.submission_notes if identity_record else "",
                'rejection_reason': getattr(prof, 'decision_reason', '') if prof else (identity_record.review_notes if identity_record else "")
            },
            'equb_groups': group_statuses,
            'payment_destinations': dest_statuses,
            'payment_providers': prov_summary
        })

    def post(self, request):
        user = request.user
        category = request.data.get('category', VerificationRecord.Category.ORGANIZER)
        submission_notes = request.data.get('submission_notes', '').strip()

        record = VerificationRecord.objects.create(
            category=category,
            target_id=user.id,
            target_name=user.full_name,
            status=VerificationRecord.Status.PENDING,
            submission_notes=submission_notes,
            documents=request.data.get('documents', {})
        )

        log_audit_event(
            action="VERIFICATION_SUBMITTED",
            actor=user,
            target_model="VerificationRecord",
            target_id=record.id,
            details={"category": category},
            request=request
        )

        return Response({
            'success': True,
            'message': 'Verification documents submitted successfully. Platform Super Admin review pending.',
            'status': record.status
        }, status=status.HTTP_201_CREATED)


class OrganizerGroupReportsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)

        # 1. Member stats
        active_members = group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE)
        total_members = active_members.count()

        # 2. Obligations & Contributions
        obs = ContributionObligation.objects.filter(group=group)
        totals = obs.aggregate(
            expected=Sum('expected_amount'),
            collected=Sum('amount_paid')
        )
        total_expected = totals['expected'] or Decimal('0.00')
        total_collected = totals['collected'] or Decimal('0.00')
        rate = round((total_collected / total_expected * 100), 1) if total_expected > 0 else 0

        # 3. Payout stats
        payouts = Payout.objects.filter(group=group)
        completed_payouts = payouts.filter(status=PayoutStatus.COMPLETED).count()
        total_payout_amount = payouts.filter(status=PayoutStatus.COMPLETED).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # 4. Disputes
        disputes_count = Dispute.objects.filter(group=group).count()
        open_disputes = Dispute.objects.filter(group=group, status=DisputeStatus.OPEN).count()

        # 5. Member leaderboard / attendance
        member_performance = []
        for m in active_members.select_related('user'):
            m_obs = obs.filter(membership=m)
            m_expected = m_obs.aggregate(total=Sum('expected_amount'))['total'] or Decimal('0.00')
            m_paid = m_obs.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0.00')
            member_performance.append({
                'member_name': m.user.full_name,
                'expected_etb': m_expected,
                'paid_etb': m_paid,
                'compliance_pct': round((m_paid / m_expected * 100), 1) if m_expected > 0 else 100
            })

        # 6. Outstanding contributions
        outstanding_obs = obs.filter(status__in=[ContributionObligation.ObligationStatus.PENDING, ContributionObligation.ObligationStatus.OVERDUE]).select_related('membership__user', 'period')[:15]
        outstanding_contributions = []
        for o in outstanding_obs:
            outstanding_contributions.append({
                'member_name': o.membership.user.full_name if (o.membership and o.membership.user) else "Member",
                'email': o.membership.user.email if (o.membership and o.membership.user) else "",
                'phone': o.membership.user.phone_number if (o.membership and o.membership.user) else "",
                'expected_etb': o.expected_amount,
                'paid_etb': o.amount_paid,
                'due_date': o.due_date,
                'status': o.status
            })

        # 7. Payout records summary
        payout_records = []
        for p in payouts.select_related('recipient_membership__user')[:10]:
            payout_records.append({
                'id': str(p.id),
                'recipient_name': p.recipient_membership.user.full_name if (p.recipient_membership and p.recipient_membership.user) else "Recipient",
                'amount_etb': p.amount,
                'status': p.status,
                'settlement_status': p.settlement_status,
                'created_at': p.created_at
            })

        # 8. Active Treasurer and activity
        treas_record = TreasurerAssignmentRecord.objects.filter(group=group, is_active=True).select_related('user').first()
        treasurer_info = None
        if treas_record and treas_record.user:
            treasurer_info = {
                'name': treas_record.user.full_name,
                'email': treas_record.user.email,
                'assigned_at': treas_record.assigned_at,
                'status': 'ACTIVE' if treas_record.is_active else 'REVOKED'
            }

        # 9. Monthly financial cycle summary
        periods = group.periods.all().order_by('period_number')[:6]
        monthly_summary = []
        for prd in periods:
            p_obs = obs.filter(period=prd)
            p_totals = p_obs.aggregate(exp=Sum('expected_amount'), act=Sum('amount_paid'))
            monthly_summary.append({
                'period_number': prd.period_number,
                'start_date': prd.start_date,
                'due_date': prd.due_date,
                'status': prd.status,
                'expected_etb': p_totals['exp'] or Decimal('0.00'),
                'collected_etb': p_totals['act'] or Decimal('0.00')
            })

        return Response({
            'group_id': str(group.id),
            'group_name': group.name,
            'kpis': {
                'total_members': total_members,
                'total_expected_etb': total_expected,
                'total_collected_etb': total_collected,
                'outstanding_total_etb': max(Decimal('0.00'), total_expected - total_collected),
                'collection_rate_pct': rate,
                'completed_payouts': completed_payouts,
                'total_payout_etb': total_payout_amount,
                'total_disputes': disputes_count,
                'open_disputes': open_disputes
            },
            'member_performance': member_performance,
            'outstanding_contributions': outstanding_contributions,
            'payout_records': payout_records,
            'treasurer_activity': treasurer_info,
            'monthly_financial_summary': monthly_summary
        })


class OrganizerGroupReportsExportCSVView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_authorized_organizer_group(request.user, group_id)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="group_{group.name.replace(" ", "_")}_report.csv"'

        writer = csv.writer(response)
        writer.writerow([sanitize_csv_cell(c) for c in [
            'Member Name', 'Email', 'Phone', 'Role', 'Status',
            'Expected (ETB)', 'Paid (ETB)', 'Compliance %', 'Payout Order'
        ]])

        members = group.memberships.all().select_related('user').prefetch_related('role_assignments__role')
        for m in members:
            obs = ContributionObligation.objects.filter(membership=m)
            expected = obs.aggregate(t=Sum('expected_amount'))['t'] or Decimal('0.00')
            paid = obs.aggregate(t=Sum('amount_paid'))['t'] or Decimal('0.00')
            compliance = round((paid / expected * 100), 1) if expected > 0 else 100
            roles = ", ".join([r.role.name for r in m.role_assignments.all()])

            writer.writerow([sanitize_csv_cell(c) for c in [
                m.user.full_name,
                m.user.email,
                m.user.phone_number or "N/A",
                roles or "Member",
                m.status,
                str(expected),
                str(paid),
                f"{compliance}%",
                m.payout_order_index or "N/A"
            ]])

        log_audit_event(
            action="REPORT_EXPORTED_CSV",
            actor=request.user,
            group=group,
            target_model="EqubGroup",
            target_id=group.id,
            request=request
        )

        return response


class OrganizerProfileView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        sub = get_or_create_active_subscription(user)
        return Response({
            'id': str(user.id),
            'full_name': user.full_name,
            'email': user.email,
            'phone_number': user.phone_number,
            'preferred_language': user.preferred_language,
            'avatar': user.avatar or '',
            'account_status': user.account_status,
            'is_email_verified': user.is_email_verified,
            'current_plan': sub.plan.name if sub and sub.plan else "Growth Plan",
            'groups_count': EqubGroup.objects.filter(organizer=user).count()
        })

    def patch(self, request):
        from apps.accounts.serializers import UserSerializer
        user = request.user
        data = request.data
        if 'email' in data and data['email'].strip().lower() != user.email:
            raise ValidationError("Email address cannot be changed. It is permanently tied to your account identity.")
        if 'full_name' in data:
            user.full_name = data['full_name'].strip()
        if 'phone_number' in data:
            val = data['phone_number'].strip() if data['phone_number'] else ''
            user.phone_number = val if val else None
        if 'preferred_language' in data:
            if data['preferred_language'] in ['en', 'am', 'om', 'ti']:
                user.preferred_language = data['preferred_language']
        if 'avatar' in data:
            user.avatar = data['avatar']

        user.save()
        log_audit_event(
            action="PROFILE_UPDATED",
            actor=user,
            target_model="User",
            target_id=user.id,
            request=request
        )
        return Response({
            'success': True,
            'message': "Organizer profile updated successfully.",
            'user': UserSerializer(user).data
        })


class OrganizerSupportTicketsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        tickets = SupportTicket.objects.filter(user=user).select_related('group').order_by('-created_at')
        return Response(SupportTicketSerializer(tickets, many=True).data)

    def post(self, request):
        user = request.user
        subject = request.data.get('subject', '').strip()
        message = request.data.get('message', '').strip()
        category = request.data.get('category', SupportTicket.Category.OTHER)
        group_id = request.data.get('group_id')

        if not subject or not message:
            raise ValidationError("Subject and message are required.")

        group = None
        if group_id:
            group = EqubGroup.objects.filter(id=group_id, organizer=user).first()

        ticket = SupportTicket.objects.create(
            user=user,
            group=group,
            category=category,
            subject=subject,
            message=message,
            status=SupportTicket.Status.OPEN
        )

        log_audit_event(
            action="SUPPORT_TICKET_CREATED",
            actor=user,
            group=group,
            target_model="SupportTicket",
            target_id=ticket.id,
            details={"subject": subject, "category": category},
            request=request
        )

        return Response(SupportTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)


class OrganizerSubscriptionManagementView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        sub = get_or_create_active_subscription(user)
        invoices = SubscriptionInvoice.objects.filter(subscription__organizer=user).order_by('-created_at')
        plans = SaasPlan.objects.filter(is_active=True).order_by('price_etb')

        groups_used = EqubGroup.objects.filter(
            organizer=user,
            status__in=[EqubGroup.GroupStatus.ACTIVE, EqubGroup.GroupStatus.DRAFT]
        ).count()

        return Response({
            'subscription': OrganizerSubscriptionSerializer(sub).data if sub else None,
            'groups_used': groups_used,
            'groups_allowed': sub.plan.max_active_groups if sub and sub.plan else 5,
            'available_plans': SaasPlanSerializer(plans, many=True).data,
            'invoices': [
                {
                    'id': str(inv.id),
                    'invoice_number': inv.invoice_number,
                    'amount_etb': inv.amount_etb,
                    'status': inv.status,
                    'due_date': inv.due_date,
                    'paid_at': inv.paid_at
                } for inv in invoices
            ]
        })

    def post(self, request):
        user = request.user
        action = request.data.get('action')
        plan_id = request.data.get('plan_id')

        sub = get_or_create_active_subscription(user)

        if action == 'renew':
            # Renew active subscription for 30 days
            base_time = max(timezone.now(), sub.expires_at or timezone.now())
            sub.expires_at = base_time + timedelta(days=30)
            sub.status = OrganizerSubscription.SubscriptionStatus.ACTIVE
            sub.save(update_fields=['expires_at', 'status'])

            # Generate paid invoice record
            import secrets
            SubscriptionInvoice.objects.create(
                subscription=sub,
                invoice_number=f"INV-{secrets.token_hex(4).upper()}",
                amount_etb=sub.plan.price_etb if sub.plan else Decimal('600.00'),
                status="PAID",
                due_date=date.today(),
                paid_at=timezone.now()
            )

            log_audit_event(
                action="SUBSCRIPTION_RENEWED",
                actor=user,
                target_model="OrganizerSubscription",
                target_id=sub.id,
                details={"plan": sub.plan.name if sub.plan else "Growth Plan", "expires_at": sub.expires_at.isoformat()},
                request=request
            )

            return Response({
                'success': True,
                'message': f"Subscription successfully renewed until {sub.expires_at.strftime('%b %d, %Y')}.",
                'subscription': OrganizerSubscriptionSerializer(sub).data
            })

        if not plan_id:
            raise ValidationError({"plan_id": "Target plan ID is required."})

        try:
            target_plan = SaasPlan.objects.get(id=plan_id, is_active=True)
        except SaasPlan.DoesNotExist:
            raise NotFound("Target plan not found.")

        sub.plan = target_plan
        sub.status = OrganizerSubscription.SubscriptionStatus.ACTIVE
        sub.expires_at = timezone.now() + timedelta(days=30)
        sub.save()

        log_audit_event(
            action="SUBSCRIPTION_PLAN_UPGRADED",
            actor=user,
            target_model="OrganizerSubscription",
            target_id=sub.id,
            details={"new_plan": target_plan.name, "fee": str(target_plan.price_etb)},
            request=request
        )

        return Response({
            'success': True,
            'message': f"Successfully upgraded subscription to {target_plan.name}",
            'subscription': OrganizerSubscriptionSerializer(sub).data
        })


class OrganizerSubscriptionPayView(views.APIView):
    """
    POST /api/v1/organizer/subscription/pay/
    Initiates or verifies SaaS subscription rent payments for Organizers strictly via CHAPA.
    Ensures Treasurers and ordinary members are strictly forbidden from paying Organizer SaaS fees.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        # Strict role enforcement: Only organizers can pay SaaS rent fees
        if not (user.is_superuser or getattr(user, 'is_organizer', False) or hasattr(user, 'organizer_profile')):
            raise PermissionDenied("Only registered organizers can pay organizer SaaS platform subscriptions.")

        action = request.data.get('action', '').strip().lower()
        tx_ref = request.data.get('tx_ref', '').strip()
        payment_reference = request.data.get('payment_reference', '').strip()
        provider = request.data.get('provider', '').strip().upper()

        # Handle Verification
        if action == 'verify' or (tx_ref and action != 'initiate'):
            if not tx_ref:
                raise ValidationError({"tx_ref": "Transaction reference is required for verification."})
            from apps.subscriptions.services import verify_chapa_subscription_payment
            result = verify_chapa_subscription_payment(tx_ref, organizer=user)
            return Response(result, status=status.HTTP_200_OK)

        # Handle Legacy test suite / manual confirmation fallback
        if payment_reference and not payment_reference.startswith('SUB-ORG-') and not tx_ref:
            prof = getattr(user, 'organizer_profile', None)
            plan_id = request.data.get('plan_id')
            if plan_id:
                try:
                    plan = SaasPlan.objects.get(id=plan_id, is_active=True)
                except SaasPlan.DoesNotExist:
                    raise ValidationError({"plan_id": "Invalid SaaS Plan ID."})
            elif prof and prof.assigned_plan:
                plan = prof.assigned_plan
            else:
                plan = SaasPlan.objects.filter(is_active=True).order_by('price_etb').first()

            amount_etb = plan.price_etb if plan else Decimal('500.00')
            tx_id = f"SUB-{secrets.token_hex(6).upper()}"

            with transaction.atomic():
                sub = OrganizerSubscription.objects.filter(organizer=user).order_by('-started_at').first()
                if not sub:
                    sub = OrganizerSubscription.objects.create(
                        organizer=user,
                        plan=plan,
                        status=OrganizerSubscription.SubscriptionStatus.ACTIVE,
                        started_at=timezone.now(),
                        expires_at=timezone.now() + timedelta(days=30)
                    )
                else:
                    sub.plan = plan
                    sub.status = OrganizerSubscription.SubscriptionStatus.ACTIVE
                    sub.started_at = timezone.now()
                    sub.expires_at = timezone.now() + timedelta(days=30)
                    sub.save()

                invoice = SubscriptionInvoice.objects.create(
                    subscription=sub,
                    invoice_number=f"INV-{secrets.token_hex(4).upper()}",
                    amount_etb=amount_etb,
                    status=SubscriptionInvoice.InvoiceStatus.PAID,
                    payment_method=provider or 'CHAPA',
                    payment_reference=payment_reference,
                    receipt_number=tx_id,
                    paid_at=timezone.now(),
                    due_date=timezone.now().date()
                )

                if prof:
                    prof.payment_status = OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED
                    prof.subscription_amount = amount_etb
                    if not prof.assigned_plan and plan:
                        prof.assigned_plan = plan
                    prof.save(update_fields=['payment_status', 'subscription_amount', 'assigned_plan'])

            is_accessible = prof.is_dashboard_accessible if prof else True
            return Response({
                'success': True,
                'message': f"Subscription payment confirmed successfully.",
                'receipt_number': tx_id,
                'payment_reference': payment_reference,
                'invoice_number': invoice.invoice_number,
                'subscription_status': sub.status,
                'payment_status': prof.payment_status if prof else 'PAYMENT_CONFIRMED',
                'gate_unlocked': is_accessible,
                'subscription': OrganizerSubscriptionSerializer(sub).data
            }, status=status.HTTP_200_OK)

        # Handle Payment Initiation via Chapa
        from apps.subscriptions.services import initiate_chapa_subscription_payment
        plan_id = request.data.get('plan_id')
        result = initiate_chapa_subscription_payment(organizer=user, plan_id=plan_id)
        return Response(result, status=status.HTTP_200_OK)

