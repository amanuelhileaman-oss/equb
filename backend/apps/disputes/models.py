import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class DisputeCategory(models.TextChoices):
    PAYMENT_NOT_RECORDED = 'PAYMENT_NOT_RECORDED', _('Payment Not Recorded or Credited')
    INCORRECT_AMOUNT = 'INCORRECT_AMOUNT', _('Incorrect Obligation or Contribution Amount')
    PAYOUT_ORDER_DISPUTE = 'PAYOUT_ORDER_DISPUTE', _('Payout Order or Rotation Sequence Discrepancy')
    RULE_VIOLATION = 'RULE_VIOLATION', _('Group Rule Violation')
    UNAUTHORIZED_ACTION = 'UNAUTHORIZED_ACTION', _('Unauthorized Financial or Membership Action')
    OTHER = 'OTHER', _('Other Operational Discrepancy')

class DisputeStatus(models.TextChoices):
    OPEN = 'OPEN', _('Open')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
    RESOLVED = 'RESOLVED', _('Resolved')
    REOPENED = 'REOPENED', _('Reopened')
    CLOSED = 'CLOSED', _('Closed')


class Dispute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        related_name='disputes'
    )
    reporter_membership = models.ForeignKey(
        'groups.GroupMembership',
        on_delete=models.PROTECT,
        related_name='disputes_reported'
    )
    category = models.CharField(
        max_length=40,
        choices=DisputeCategory.choices,
        default=DisputeCategory.OTHER
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=DisputeStatus.choices,
        default=DisputeStatus.OPEN,
        db_index=True
    )
    assigned_handler = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='handled_disputes'
    )
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'disputes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Dispute #{self.id}: {self.title} [{self.status}]"


class DisputeEvidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispute = models.ForeignKey(
        Dispute,
        on_delete=models.CASCADE,
        related_name='evidence_attachments'
    )
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    file = models.FileField(upload_to='dispute_evidence/')
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'dispute_evidence'

    def __str__(self):
        return f"Evidence for Dispute #{self.dispute.id} by {self.uploader.full_name}"
