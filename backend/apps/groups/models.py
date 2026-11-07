import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

class EqubGroup(models.Model):
    class GroupStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PENDING_APPROVAL = 'PENDING_APPROVAL', _('Pending Approval')
        ACTIVE = 'ACTIVE', _('Active')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        CLOSED = 'CLOSED', _('Closed')

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = 'UNVERIFIED', _('Unverified')
        PENDING = 'PENDING', _('Pending Verification')
        VERIFIED = 'VERIFIED', _('Verified')
        REJECTED = 'REJECTED', _('Rejected')

    class Frequency(models.TextChoices):
        WEEKLY = 'WEEKLY', _('Weekly')
        BIWEEKLY = 'BIWEEKLY', _('Biweekly')
        MONTHLY = 'MONTHLY', _('Monthly')

    class PayoutMethod(models.TextChoices):
        ROTATION_ORDER = 'ROTATION_ORDER', _('Fixed Rotation Order')
        LOTTERY_DRAW = 'LOTTERY_DRAW', _('Lottery / Random Draw')

    class LotteryMethod(models.TextChoices):
        METHOD_A = 'METHOD_A', _('Method A – One-time lottery')
        METHOD_B = 'METHOD_B', _('Method B – Round-by-round lottery')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    group_purpose = models.CharField(max_length=255, blank=True)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='organized_groups'
    )
    status = models.CharField(
        max_length=25,
        choices=GroupStatus.choices,
        default=GroupStatus.DRAFT,
        db_index=True
    )
    verification_status = models.CharField(
        max_length=25,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
        db_index=True
    )
    currency = models.CharField(max_length=10, default='ETB')
    contribution_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('1000.00'))
    contribution_frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.MONTHLY
    )
    capacity = models.PositiveIntegerField(default=12)
    start_date = models.DateField()
    payout_method = models.CharField(
        max_length=25,
        choices=PayoutMethod.choices,
        default=PayoutMethod.ROTATION_ORDER
    )
    lottery_method = models.CharField(
        max_length=20,
        choices=LotteryMethod.choices,
        default=LotteryMethod.METHOD_A,
        help_text=_("Option A (One-time lottery for full cycle order) or Option B (Round-by-round lottery).")
    )
    grace_period_days = models.PositiveIntegerField(
        default=3,
        help_text=_("Grace period in days for overdue contributions before resolution workflow triggers.")
    )
    is_lottery_locked = models.BooleanField(
        default=False,
        help_text=_("Locks the lottery method once the Equb cycle begins to prevent silent alterations.")
    )
    current_cycle_number = models.PositiveIntegerField(
        default=1,
        help_text=_("Current active cycle sequence number for this Equb group.")
    )
    allowed_payment_methods = models.JSONField(
        default=list,
        help_text=_("List of allowed methods: DIGITAL_PROVIDER, CASH, BANK_TRANSFER")
    )
    rules_approval_threshold_percent = models.PositiveIntegerField(
        default=100,
        help_text=_("Percentage of member votes required to enact new rule versions (e.g. 100 for unanimous, 67 for supermajority).")
    )
    require_cash_second_confirmation = models.BooleanField(
        default=False,
        help_text=_("Requires an organizer or secondary treasurer to confirm cash entries recorded by the treasurer.")
    )
    active_rules_version = models.ForeignKey(
        'rules.RuleVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    # Chapa Subaccount for direct group bank settlement
    chapa_subaccount_id = models.CharField(max_length=100, blank=True, default='', help_text=_("Chapa Subaccount ID for direct split routing."))
    bank_code = models.CharField(max_length=50, blank=True, default='', help_text=_("Chapa Bank Code / ID."))
    bank_name = models.CharField(max_length=150, blank=True, default='')
    bank_account_name = models.CharField(max_length=150, blank=True, default='')
    bank_account_number = models.CharField(max_length=100, blank=True, default='')
    suspension_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'groups'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'verification_status']),
            models.Index(fields=['organizer', 'status']),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"


class GroupMembership(models.Model):
    class MembershipStatus(models.TextChoices):
        INVITED = 'INVITED', _('Invited')
        REQUESTED = 'REQUESTED', _('Requested')
        ACTIVE = 'ACTIVE', _('Active')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        REMOVED = 'REMOVED', _('Removed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        EqubGroup,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='group_memberships'
    )
    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.INVITED,
        db_index=True
    )
    payout_order_index = models.PositiveIntegerField(null=True, blank=True)
    joined_at = models.DateTimeField(null=True, blank=True)
    accepted_rules_version = models.ForeignKey(
        'rules.RuleVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'group_memberships'
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'user'],
                name='unique_group_membership'
            )
        ]
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self):
        return f"{self.user.full_name} in {self.group.name} [{self.status}]"


class GroupInvitation(models.Model):
    class InvitationStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        ACCEPTED = 'ACCEPTED', _('Accepted')
        EXPIRED = 'EXPIRED', _('Expired')
        CANCELLED = 'CANCELLED', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        EqubGroup,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    invited_email = models.EmailField(db_index=True)
    token = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'group_invitations'

    def __str__(self):
        return f"Invite for {self.invited_email} to {self.group.name}"


class TreasurerAssignmentRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        EqubGroup,
        on_delete=models.CASCADE,
        related_name='treasurer_history'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='treasurer_assignments'
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='treasurers_assigned'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='treasurers_revoked'
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'treasurer_assignment_records'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['group', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        status_str = "ACTIVE" if self.is_active else "REVOKED"
        return f"{self.user.full_name} as Treasurer in {self.group.name} [{status_str}]"


# ==============================================================================
# 1. EQUB CYCLE MODEL (Multi-Cycle Management & Completion)
# ==============================================================================
class EqubCycle(models.Model):
    class CycleStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        ACTIVE = 'ACTIVE', _('Active Cycle')
        COMPLETED = 'COMPLETED', _('Completed Cycle')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        EqubGroup,
        on_delete=models.CASCADE,
        related_name='cycles'
    )
    cycle_number = models.PositiveIntegerField(default=1)
    lottery_method = models.CharField(
        max_length=20,
        choices=EqubGroup.LotteryMethod.choices,
        default=EqubGroup.LotteryMethod.METHOD_A
    )
    status = models.CharField(
        max_length=20,
        choices=CycleStatus.choices,
        default=CycleStatus.ACTIVE,
        db_index=True
    )
    start_date = models.DateField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_report = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'equb_cycles'
        ordering = ['group', 'cycle_number']
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'cycle_number'],
                name='unique_cycle_per_group'
            )
        ]

    def __str__(self):
        return f"{self.group.name} - Cycle #{self.cycle_number} [{self.status}]"


# ==============================================================================
# 2. LOTTERY ROUND & RESULTS (Method A & Method B Execution)
# ==============================================================================
class LotteryRound(models.Model):
    class RoundStatus(models.TextChoices):
        SCHEDULED = 'SCHEDULED', _('Scheduled')
        POSTPONED = 'POSTPONED', _('Postponed (Incomplete Contributions)')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey(
        EqubCycle,
        on_delete=models.CASCADE,
        related_name='lottery_rounds'
    )
    group = models.ForeignKey(
        EqubGroup,
        on_delete=models.CASCADE,
        related_name='lottery_rounds'
    )
    period = models.ForeignKey(
        'contributions.ContributionPeriod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lottery_rounds'
    )
    round_number = models.PositiveIntegerField()
    lottery_method = models.CharField(
        max_length=20,
        choices=EqubGroup.LotteryMethod.choices
    )
    status = models.CharField(
        max_length=35,
        choices=RoundStatus.choices,
        default=RoundStatus.SCHEDULED,
        db_index=True
    )
    scheduled_time = models.DateTimeField()
    executed_at = models.DateTimeField(null=True, blank=True)
    winner_membership = models.ForeignKey(
        GroupMembership,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='lottery_wins'
    )
    postponed_reason = models.TextField(blank=True, default='')
    eligible_members_snapshot = models.JSONField(default=list, blank=True)
    audit_hash = models.CharField(max_length=128, blank=True, default='')
    audit_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lottery_rounds'
        ordering = ['cycle', 'round_number']
        constraints = [
            models.UniqueConstraint(
                fields=['cycle', 'round_number'],
                name='unique_lottery_round_per_cycle'
            )
        ]

    def __str__(self):
        winner_name = self.winner_membership.user.full_name if self.winner_membership else "TBD"
        return f"{self.group.name} Cycle #{self.cycle.cycle_number} Round #{self.round_number} -> {winner_name} [{self.status}]"


class LotteryResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cycle = models.ForeignKey(
        EqubCycle,
        on_delete=models.CASCADE,
        related_name='lottery_results'
    )
    lottery_round = models.ForeignKey(
        LotteryRound,
        on_delete=models.CASCADE,
        related_name='results'
    )
    round_number = models.PositiveIntegerField()
    winner_membership = models.ForeignKey(
        GroupMembership,
        on_delete=models.PROTECT,
        related_name='won_lottery_results'
    )
    draw_timestamp = models.DateTimeField(default=timezone.now)
    lottery_method = models.CharField(max_length=20)
    verification_hash = models.CharField(max_length=128, blank=True, default='')
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lottery_results'
        ordering = ['cycle', 'round_number']
        constraints = [
            models.UniqueConstraint(
                fields=['cycle', 'round_number'],
                name='unique_lottery_result_round'
            ),
            models.UniqueConstraint(
                fields=['cycle', 'winner_membership'],
                name='unique_cycle_winner_once'
            )
        ]

    def __str__(self):
        return f"Cycle #{self.cycle.cycle_number} R#{self.round_number}: Winner {self.winner_membership.user.full_name}"


# ==============================================================================
# 3. OVERDUE CONTRIBUTIONS & RESOLUTION SYSTEM (Dropdown 2: A, B, C)
# ==============================================================================
class OverdueCase(models.Model):
    class CaseStatus(models.TextChoices):
        GRACE_PERIOD = 'GRACE_PERIOD', _('Grace Period Active')
        EXPIRED = 'EXPIRED', _('Grace Period Expired - Action Required')
        RESOLVED_WAITING = 'RESOLVED_WAITING', _('Resolution: Continue Waiting')
        RESOLVED_AGREEMENT = 'RESOLVED_AGREEMENT', _('Resolution: Formal Payment Agreement')
        RESOLVED_REVIEW = 'RESOLVED_REVIEW', _('Resolution: Membership Review')
        CLOSED_PAID = 'CLOSED_PAID', _('Resolved - Fully Paid')
        CANCELLED = 'CANCELLED', _('Cancelled')

    class ResolutionChoice(models.TextChoices):
        CONTINUE_WAITING = 'CONTINUE_WAITING', _('A. Continue waiting')
        PAYMENT_AGREEMENT = 'PAYMENT_AGREEMENT', _('B. Formal payment agreement')
        MEMBERSHIP_REVIEW = 'MEMBERSHIP_REVIEW', _('C. Membership review')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        EqubGroup,
        on_delete=models.CASCADE,
        related_name='overdue_cases'
    )
    membership = models.ForeignKey(
        GroupMembership,
        on_delete=models.PROTECT,
        related_name='overdue_cases'
    )
    obligation = models.ForeignKey(
        'contributions.ContributionObligation',
        on_delete=models.PROTECT,
        related_name='overdue_cases'
    )
    period = models.ForeignKey(
        'contributions.ContributionPeriod',
        on_delete=models.CASCADE,
        related_name='overdue_cases'
    )
    outstanding_amount = models.DecimalField(max_digits=12, decimal_places=2)
    original_deadline = models.DateField()
    grace_period_days = models.PositiveIntegerField(default=3)
    grace_period_expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=35,
        choices=CaseStatus.choices,
        default=CaseStatus.GRACE_PERIOD,
        db_index=True
    )
    selected_resolution = models.CharField(
        max_length=30,
        choices=ResolutionChoice.choices,
        null=True,
        blank=True
    )
    resolution_reason = models.TextField(blank=True, default='')
    follow_up_date = models.DateField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_overdue_cases'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    history_log = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'overdue_cases'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['membership', 'status']),
        ]

    def __str__(self):
        return f"Overdue: {self.membership.user.full_name} for {self.group.name} ({self.status})"

    @property
    def is_grace_period_active(self) -> bool:
        return timezone.now() <= self.grace_period_expires_at and self.status == self.CaseStatus.GRACE_PERIOD

    @property
    def days_overdue(self) -> int:
        delta = (timezone.now().date() - self.original_deadline).days
        return max(0, delta)


class PaymentAgreement(models.Model):
    class AgreementStatus(models.TextChoices):
        PENDING_MEMBER_ACCEPTANCE = 'PENDING_MEMBER_ACCEPTANCE', _('Pending Member Acceptance')
        ACCEPTED_BY_MEMBER = 'ACCEPTED_BY_MEMBER', _('Accepted by Member')
        REJECTED_BY_MEMBER = 'REJECTED_BY_MEMBER', _('Rejected by Member')
        APPROVED_BY_GROUP = 'APPROVED_BY_GROUP', _('Approved by Group')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        FULFILLED = 'FULFILLED', _('Fulfilled')
        DEFAULTED = 'DEFAULTED', _('Defaulted')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    overdue_case = models.ForeignKey(
        OverdueCase,
        on_delete=models.CASCADE,
        related_name='payment_agreements'
    )
    group = models.ForeignKey(
        EqubGroup,
        on_delete=models.CASCADE,
        related_name='payment_agreements'
    )
    membership = models.ForeignKey(
        GroupMembership,
        on_delete=models.PROTECT,
        related_name='payment_agreements'
    )
    total_outstanding_amount = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2)
    member_reason = models.TextField()
    status = models.CharField(
        max_length=35,
        choices=AgreementStatus.choices,
        default=AgreementStatus.PENDING_MEMBER_ACCEPTANCE,
        db_index=True
    )
    member_accepted_at = models.DateTimeField(null=True, blank=True)
    member_rejection_reason = models.TextField(blank=True, default='')
    group_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payment_agreements'
    )
    group_approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_payment_agreements'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_agreements'
        ordering = ['-created_at']

    def __str__(self):
        return f"Agreement for {self.membership.user.full_name}: {self.remaining_balance}/{self.total_outstanding_amount} ETB [{self.status}]"


class PaymentInstallment(models.Model):
    class InstallmentStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PAID = 'PAID', _('Paid & Verified')
        OVERDUE = 'OVERDUE', _('Overdue')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agreement = models.ForeignKey(
        PaymentAgreement,
        on_delete=models.CASCADE,
        related_name='installments'
    )
    installment_number = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=InstallmentStatus.choices,
        default=InstallmentStatus.PENDING,
        db_index=True
    )
    chapa_tx_ref = models.CharField(max_length=100, blank=True, default='')
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_installments'
        ordering = ['agreement', 'installment_number']
        constraints = [
            models.UniqueConstraint(
                fields=['agreement', 'installment_number'],
                name='unique_agreement_installment_num'
            )
        ]

    def __str__(self):
        return f"Installment #{self.installment_number}: {self.amount} ETB due {self.due_date} [{self.status}]"


class MembershipReview(models.Model):
    class ReviewStatus(models.TextChoices):
        OPEN = 'OPEN', _('Review Open - Awaiting Decision')
        DECIDED = 'DECIDED', _('Decision Rendered')
        COMPLETED = 'COMPLETED', _('Completed & Settled')
        CANCELLED = 'CANCELLED', _('Cancelled')

    class ReviewDecision(models.TextChoices):
        REPLACE_MEMBER = 'REPLACE_MEMBER', _('Replace Member with Approved Candidate')
        REMOVE_MEMBER = 'REMOVE_MEMBER', _('Remove Member & Forfeit Slot')
        REINSTATE_MEMBER = 'REINSTATE_MEMBER', _('Reinstate Member after Settlement')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    overdue_case = models.ForeignKey(
        OverdueCase,
        on_delete=models.CASCADE,
        related_name='membership_reviews'
    )
    group = models.ForeignKey(
        EqubGroup,
        on_delete=models.CASCADE,
        related_name='membership_reviews'
    )
    membership = models.ForeignKey(
        GroupMembership,
        on_delete=models.PROTECT,
        related_name='membership_reviews'
    )
    documented_reason = models.TextField()
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='initiated_membership_reviews'
    )
    member_response = models.TextField(blank=True, default='')
    member_responded_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=25,
        choices=ReviewStatus.choices,
        default=ReviewStatus.OPEN,
        db_index=True
    )
    decision = models.CharField(
        max_length=30,
        choices=ReviewDecision.choices,
        null=True,
        blank=True
    )
    decision_reason = models.TextField(blank=True, default='')
    decision_date = models.DateTimeField(null=True, blank=True)
    approvers_list = models.JSONField(default=list, blank=True)
    previous_contributions_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    previous_payouts_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_obligation_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    replacement_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replacing_reviews'
    )
    replacement_terms_accepted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'membership_reviews'
        ordering = ['-created_at']

    def __str__(self):
        return f"Membership Review for {self.membership.user.full_name} in {self.group.name} [{self.status}]"

