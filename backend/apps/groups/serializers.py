from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import (
    EqubGroup, GroupMembership, GroupInvitation,
    EqubCycle, LotteryRound, LotteryResult, OverdueCase,
    PaymentAgreement, PaymentInstallment, MembershipReview
)
from apps.accounts.serializers import UserSerializer
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.subscriptions.services import validate_organizer_group_limit
from apps.rules.models import RuleVersion

class GroupMembershipSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = GroupMembership
        fields = ['id', 'user', 'status', 'payout_order_index', 'joined_at', 'roles']

    def get_roles(self, obj):
        return list(obj.role_assignments.values_list('role__code', flat=True))


class EqubGroupSerializer(serializers.ModelSerializer):
    organizer = UserSerializer(read_only=True)
    active_members_count = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = EqubGroup
        fields = [
            'id', 'name', 'description', 'group_purpose', 'organizer',
            'status', 'verification_status', 'currency', 'contribution_amount',
            'contribution_frequency', 'capacity', 'start_date', 'payout_method',
            'lottery_method', 'grace_period_days', 'is_lottery_locked', 'current_cycle_number',
            'allowed_payment_methods', 'rules_approval_threshold_percent',
            'require_cash_second_confirmation', 'active_rules_version',
            'chapa_subaccount_id', 'bank_code', 'bank_name', 'bank_account_name', 'bank_account_number',
            'active_members_count', 'my_role', 'created_at'
        ]

    def get_active_members_count(self, obj):
        return obj.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()

    def get_my_role(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user).first()
        if not membership:
            return None
        return list(membership.role_assignments.values_list('role__code', flat=True))


class GroupCreateSerializer(serializers.ModelSerializer):
    terms_text = serializers.CharField(write_only=True, required=False, default="")
    participate_as_member = serializers.BooleanField(write_only=True, required=False, default=False)

    def to_internal_value(self, data):
        if 'max_members' in data and 'capacity' not in data:
            data = data.copy() if hasattr(data, 'copy') else dict(data)
            data['capacity'] = data['max_members']
        return super().to_internal_value(data)

    class Meta:
        model = EqubGroup
        fields = [
            'name', 'description', 'group_purpose', 'contribution_amount',
            'contribution_frequency', 'capacity', 'start_date', 'payout_method',
            'lottery_method', 'grace_period_days',
            'allowed_payment_methods', 'rules_approval_threshold_percent',
            'require_cash_second_confirmation', 'terms_text', 'participate_as_member'
        ]

    def validate_contribution_amount(self, value):
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("Contribution amount must be greater than zero ETB.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        organizer = request.user
        participate_as_member = validated_data.pop('participate_as_member', False)

        # Enforce server-side SaaS subscription limit
        validate_organizer_group_limit(organizer)

        terms_text = validated_data.pop('terms_text', "") or (
            f"Equb rules for {validated_data['name']}: Contribution amount of {validated_data['contribution_amount']} ETB "
            f"payable on a {validated_data['contribution_frequency'].lower()} basis. Payout by {validated_data['payout_method'].lower()}."
        )

        # Always derive organizer from server-side authenticated session
        group = EqubGroup.objects.create(
            organizer=organizer,
            status=EqubGroup.GroupStatus.PENDING_APPROVAL,
            verification_status=EqubGroup.VerificationStatus.PENDING,
            currency='ETB',
            **validated_data
        )

        # Create organizer membership and assign GROUP_ORGANIZER role
        org_membership = GroupMembership.objects.create(
            group=group,
            user=organizer,
            status=GroupMembership.MembershipStatus.ACTIVE,
            payout_order_index=1 if participate_as_member else None,
            joined_at=timezone.now()
        )
        organizer_role, _ = GroupRole.objects.get_or_create(
            group=None,
            code="GROUP_ORGANIZER",
            defaults={"name": "Group Organizer", "is_system_role": True}
        )
        MembershipRoleAssignment.objects.create(
            membership=org_membership,
            role=organizer_role,
            assigned_by=organizer
        )

        # If organizer opted to join as a rotating member:
        if participate_as_member:
            member_role, _ = GroupRole.objects.get_or_create(
                group=None,
                code="GROUP_MEMBER",
                defaults={"name": "Group Member", "is_system_role": True}
            )
            MembershipRoleAssignment.objects.create(
                membership=org_membership,
                role=member_role,
                assigned_by=organizer
            )

        # Propose initial rule charter v1
        rule_v1 = RuleVersion.objects.create(
            group=group,
            version_number=1,
            title=f"{group.name} Charter v1",
            terms_text=terms_text,
            contribution_amount=group.contribution_amount,
            contribution_frequency=group.contribution_frequency,
            payout_method=group.payout_method,
            approval_threshold_percent=group.rules_approval_threshold_percent,
            status=RuleVersion.RuleStatus.PROPOSED,
            proposed_by=organizer
        )
        group.active_rules_version = rule_v1
        group.save(update_fields=['active_rules_version'])

        return group


class GroupInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupInvitation
        fields = ['id', 'invited_email', 'status', 'created_at', 'expires_at']
        read_only_fields = ['id', 'status', 'created_at', 'expires_at']


# ==============================================================================
# SERIALIZERS FOR LOTTERY, CYCLES, OVERDUE & RESOLUTIONS
# ==============================================================================
class EqubCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EqubCycle
        fields = [
            'id', 'group', 'cycle_number', 'lottery_method', 'status',
            'start_date', 'completed_at', 'completion_report', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at', 'completion_report']


class LotteryResultSerializer(serializers.ModelSerializer):
    winner_name = serializers.CharField(source='winner_membership.user.full_name', read_only=True)
    winner_email = serializers.CharField(source='winner_membership.user.email', read_only=True)

    class Meta:
        model = LotteryResult
        fields = [
            'id', 'cycle', 'lottery_round', 'round_number', 'winner_membership',
            'winner_name', 'winner_email', 'draw_timestamp', 'lottery_method',
            'verification_hash', 'details', 'created_at'
        ]
        read_only_fields = ['id', 'draw_timestamp', 'verification_hash', 'created_at']


class LotteryRoundSerializer(serializers.ModelSerializer):
    winner_name = serializers.CharField(source='winner_membership.user.full_name', read_only=True)
    winner_email = serializers.CharField(source='winner_membership.user.email', read_only=True)
    cycle_number = serializers.IntegerField(source='cycle.cycle_number', read_only=True)

    class Meta:
        model = LotteryRound
        fields = [
            'id', 'cycle', 'cycle_number', 'group', 'period', 'round_number',
            'lottery_method', 'status', 'scheduled_time', 'executed_at',
            'winner_membership', 'winner_name', 'winner_email', 'postponed_reason',
            'eligible_members_snapshot', 'audit_hash', 'audit_metadata', 'created_at'
        ]
        read_only_fields = ['id', 'executed_at', 'audit_hash', 'created_at']


class PaymentInstallmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentInstallment
        fields = [
            'id', 'agreement', 'installment_number', 'amount', 'amount_paid',
            'due_date', 'status', 'chapa_tx_ref', 'verified_at', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'amount_paid', 'status', 'chapa_tx_ref', 'verified_at', 'created_at']


class PaymentAgreementSerializer(serializers.ModelSerializer):
    installments = PaymentInstallmentSerializer(many=True, read_only=True)
    member_name = serializers.CharField(source='membership.user.full_name', read_only=True)
    member_email = serializers.CharField(source='membership.user.email', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = PaymentAgreement
        fields = [
            'id', 'overdue_case', 'group', 'group_name', 'membership',
            'member_name', 'member_email', 'total_outstanding_amount',
            'remaining_balance', 'member_reason', 'status',
            'member_accepted_at', 'member_rejection_reason',
            'group_approved_by', 'group_approved_at', 'created_by',
            'installments', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'remaining_balance', 'member_accepted_at',
            'group_approved_by', 'group_approved_at', 'created_by',
            'created_at', 'updated_at'
        ]


class MembershipReviewSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='membership.user.full_name', read_only=True)
    member_email = serializers.CharField(source='membership.user.email', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    replacement_name = serializers.CharField(source='replacement_user.full_name', read_only=True)

    class Meta:
        model = MembershipReview
        fields = [
            'id', 'overdue_case', 'group', 'group_name', 'membership',
            'member_name', 'member_email', 'documented_reason', 'initiated_by',
            'member_response', 'member_responded_at', 'status', 'decision',
            'decision_reason', 'decision_date', 'approvers_list',
            'previous_contributions_total', 'previous_payouts_total',
            'net_obligation_balance', 'replacement_user', 'replacement_name',
            'replacement_terms_accepted', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'initiated_by', 'previous_contributions_total',
            'previous_payouts_total', 'net_obligation_balance',
            'created_at', 'updated_at'
        ]


class OverdueCaseSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='membership.user.full_name', read_only=True)
    member_email = serializers.CharField(source='membership.user.email', read_only=True)
    member_phone = serializers.CharField(source='membership.user.phone_number', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    period_number = serializers.IntegerField(source='period.period_number', read_only=True)
    is_grace_period_active = serializers.BooleanField(read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)
    payment_agreement = serializers.SerializerMethodField()
    membership_review = serializers.SerializerMethodField()

    class Meta:
        model = OverdueCase
        fields = [
            'id', 'group', 'group_name', 'membership', 'member_name',
            'member_email', 'member_phone', 'obligation', 'period',
            'period_number', 'outstanding_amount', 'original_deadline',
            'grace_period_days', 'grace_period_expires_at', 'status',
            'selected_resolution', 'resolution_reason', 'follow_up_date',
            'resolved_by', 'resolved_at', 'history_log',
            'is_grace_period_active', 'days_overdue',
            'payment_agreement', 'membership_review',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'outstanding_amount', 'original_deadline',
            'grace_period_expires_at', 'resolved_by', 'resolved_at',
            'created_at', 'updated_at'
        ]

    def get_payment_agreement(self, obj):
        agreement = obj.payment_agreements.first()
        return PaymentAgreementSerializer(agreement).data if agreement else None

    def get_membership_review(self, obj):
        review = obj.membership_reviews.first()
        return MembershipReviewSerializer(review).data if review else None
