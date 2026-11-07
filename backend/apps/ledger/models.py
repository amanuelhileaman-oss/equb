import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class LedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CONTRIBUTION_RECEIVED = 'CONTRIBUTION_RECEIVED', _('Contribution Received')
        CONTRIBUTION_REVERSED = 'CONTRIBUTION_REVERSED', _('Contribution Reversed')
        PAYOUT_DISBURSED = 'PAYOUT_DISBURSED', _('Payout Disbursed')
        PAYOUT_REVERSED = 'PAYOUT_REVERSED', _('Payout Reversed')
        MANUAL_ADJUSTMENT = 'MANUAL_ADJUSTMENT', _('Authorized Manual Adjustment')

    class Direction(models.TextChoices):
        CREDIT = 'CREDIT', _('Credit (Funds In)')
        DEBIT = 'DEBIT', _('Debit (Funds Out)')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.PROTECT,
        related_name='ledger_entries'
    )
    entry_type = models.CharField(max_length=40, choices=EntryType.choices)
    direction = models.CharField(max_length=10, choices=Direction.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=10, default='ETB')
    
    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ledger_records'
    )
    payout = models.ForeignKey(
        'payouts.Payout',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ledger_records'
    )
    reversal_of = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reversals'
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='ledger_entries_posted'
    )
    posted_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField()

    class Meta:
        db_table = 'ledger_entries'
        ordering = ['posted_at']
        indexes = [
            models.Index(fields=['group', 'posted_at']),
            models.Index(fields=['entry_type', 'posted_at']),
        ]

    def __str__(self):
        return f"{self.group.name}: {self.direction} {self.amount} {self.currency} ({self.entry_type})"
