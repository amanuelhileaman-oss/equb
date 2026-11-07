import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class PayoutStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    PENDING_APPROVAL = 'PENDING_APPROVAL', _('Pending Independent Approval')
    APPROVED = 'APPROVED', _('Approved for Execution')
    EXECUTING = 'EXECUTING', _('Executing')
    COMPLETED = 'COMPLETED', _('Completed & Confirmed')
    FAILED = 'FAILED', _('Execution Failed')
    BLOCKED_INSUFFICIENT_FUNDS = 'BLOCKED_INSUFFICIENT_FUNDS', _('Blocked: Insufficient Group Funds')

class PayoutSettlementStatus(models.TextChoices):
    NOT_APPLICABLE = 'NOT_APPLICABLE', _('Not Applicable')
    AWAITING_SETTLEMENT = 'AWAITING_SETTLEMENT', _('Awaiting Bank Settlement')
    SETTLED = 'SETTLED', _('Settled')
    SETTLEMENT_EXCEPTION = 'SETTLEMENT_EXCEPTION', _('Settlement Exception')


class Payout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        related_name='payouts'
    )
    period = models.ForeignKey(
        'contributions.ContributionPeriod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payouts'
    )
    recipient_membership = models.ForeignKey(
        'groups.GroupMembership',
        on_delete=models.PROTECT,
        related_name='payouts_received'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='ETB')
    status = models.CharField(
        max_length=30,
        choices=PayoutStatus.choices,
        default=PayoutStatus.DRAFT,
        db_index=True
    )
    settlement_status = models.CharField(
        max_length=30,
        choices=PayoutSettlementStatus.choices,
        default=PayoutSettlementStatus.NOT_APPLICABLE
    )
    requesting_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='requested_payouts'
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    executed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='executed_payouts'
    )
    executed_at = models.DateTimeField(null=True, blank=True)
    execution_reference = models.CharField(max_length=120, blank=True)
    settlement_evidence_file = models.FileField(upload_to='payout_evidence/', blank=True, null=True)
    blocking_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payouts'
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['recipient_membership', 'status']),
        ]

    def __str__(self):
        return f"Payout {self.amount} {self.currency} to {self.recipient_membership.user.full_name} [{self.status}]"


class PayoutApproval(models.Model):
    class Decision(models.TextChoices):
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payout = models.ForeignKey(
        Payout,
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payout_approvals'
    )
    decision = models.CharField(max_length=20, choices=Decision.choices, default=Decision.APPROVED)
    reason = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payout_approvals'
        constraints = [
            models.UniqueConstraint(
                fields=['payout', 'approver'],
                name='unique_payout_approval_per_approver'
            )
        ]

    def __str__(self):
        return f"{self.approver.full_name} -> {self.decision} on Payout {self.payout.id}"
