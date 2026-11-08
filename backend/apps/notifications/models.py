import uuid
from django.db import models
from django.conf import settings

class Notification(models.Model):
    class NotificationType(models.TextChoices):
        CONTRIBUTION_DUE = 'CONTRIBUTION_DUE', 'Contribution Due'
        CONTRIBUTION_DEADLINE = 'CONTRIBUTION_DEADLINE', 'Contribution Deadline'
        PAYMENT_RECEIVED = 'PAYMENT_RECEIVED', 'Payment Received'
        CASH_VERIFICATION_REQUEST = 'CASH_VERIFICATION_REQUEST', 'Cash Dual-Confirmation Request'
        BANK_RECONCILIATION_REQUEST = 'BANK_RECONCILIATION_REQUEST', 'Bank Transfer Reconciliation'
        RULE_PROPOSAL = 'RULE_PROPOSAL', 'Rule Amendment Proposal'
        RULE_APPROVED = 'RULE_APPROVED', 'Rule Activated'
        PAYOUT_READY = 'PAYOUT_READY', 'Payout Ready'
        PAYOUT_EXECUTED = 'PAYOUT_EXECUTED', 'Payout Executed'
        DISPUTE_FILED = 'DISPUTE_FILED', 'Dispute Filed'
        MAINTENANCE = 'MAINTENANCE', 'System Maintenance'
        NEW_FEATURE = 'NEW_FEATURE', 'New Feature'
        SUBSCRIPTION_RENEWAL = 'SUBSCRIPTION_RENEWAL', 'Subscription Renewal'
        VERIFICATION_DECISION = 'VERIFICATION_DECISION', 'Verification Decision'
        OVERDUE_CONTRIBUTION = 'OVERDUE_CONTRIBUTION', 'Overdue Contribution Alert'
        GRACE_PERIOD_STARTED = 'GRACE_PERIOD_STARTED', 'Grace Period Started'
        GRACE_PERIOD_EXPIRED = 'GRACE_PERIOD_EXPIRED', 'Grace Period Expired'
        LOTTERY_POSTPONED = 'LOTTERY_POSTPONED', 'Lottery Draw Postponed'
        LOTTERY_EXECUTED = 'LOTTERY_EXECUTED', 'Lottery Draw Executed'
        NEW_LOTTERY_WINNER = 'NEW_LOTTERY_WINNER', 'New Lottery Winner'
        PAYMENT_AGREEMENT_PROPOSED = 'PAYMENT_AGREEMENT_PROPOSED', 'Payment Agreement Proposed'
        PAYMENT_AGREEMENT_APPROVED = 'PAYMENT_AGREEMENT_APPROVED', 'Payment Agreement Approved'
        INSTALLMENT_APPROACHING = 'INSTALLMENT_APPROACHING', 'Installment Due Approaching'
        INSTALLMENT_OVERDUE = 'INSTALLMENT_OVERDUE', 'Installment Overdue'
        MEMBERSHIP_REVIEW_INITIATED = 'MEMBERSHIP_REVIEW_INITIATED', 'Membership Review Initiated'
        MEMBERSHIP_REVIEW_DECISION = 'MEMBERSHIP_REVIEW_DECISION', 'Membership Review Decision'
        NEW_CYCLE_CREATED = 'NEW_CYCLE_CREATED', 'New Cycle Initialized'
        GENERAL = 'GENERAL', 'General System Alert'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    title = models.CharField(max_length=255)
    title_am = models.CharField(max_length=255, blank=True, default='')
    message = models.TextField()
    message_am = models.TextField(blank=True, default='')
    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL
    )
    is_read = models.BooleanField(default=False)
    link_url = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.title} ({'Read' if self.is_read else 'Unread'})"


class ChatMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_chat_messages'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_chat_messages'
    )
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_messages'
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['sender', 'recipient', 'created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"Chat from {self.sender.email} to {self.recipient.email} at {self.created_at}"

