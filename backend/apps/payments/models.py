import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class PaymentMethod(models.TextChoices):
    DIGITAL_PROVIDER = 'DIGITAL_PROVIDER', _('Digital Payment (Telebirr / CBE Birr)')
    CASH = 'CASH', _('Cash Paid to Treasurer')
    BANK_TRANSFER = 'BANK_TRANSFER', _('Bank / Mobile Money Transfer')

class PaymentStatus(models.TextChoices):
    INITIATED = 'INITIATED', _('Initiated')
    PENDING_VERIFICATION = 'PENDING_VERIFICATION', _('Pending Verification')
    CONFIRMED = 'CONFIRMED', _('Confirmed')
    FAILED = 'FAILED', _('Failed')
    EXPIRED = 'EXPIRED', _('Expired')
    REVERSED = 'REVERSED', _('Reversed')
    REFUNDED = 'REFUNDED', _('Refunded')
    DISPUTED = 'DISPUTED', _('Disputed')

class SettlementStatus(models.TextChoices):
    NOT_APPLICABLE = 'NOT_APPLICABLE', _('Not Applicable')
    AWAITING_SETTLEMENT = 'AWAITING_SETTLEMENT', _('Awaiting Settlement')
    SETTLED = 'SETTLED', _('Settled')
    SETTLEMENT_EXCEPTION = 'SETTLEMENT_EXCEPTION', _('Settlement Exception')


class GroupPaymentDestination(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        related_name='payment_destinations'
    )
    provider_or_bank = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=50, blank=True, default='', help_text=_("Chapa Bank Code / ID."))
    chapa_subaccount_id = models.CharField(max_length=100, blank=True, default='', help_text=_("Chapa Subaccount ID for direct split routing."))
    account_name = models.CharField(max_length=150)
    account_number = models.CharField(max_length=100)
    branch_or_details = models.CharField(max_length=200, blank=True)
    transfer_instructions = models.TextField(blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_destinations'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'group_payment_destinations'

    def __str__(self):
        return f"{self.group.name} - {self.provider_or_bank} ({self.account_number})"


class PaymentAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    internal_reference = models.CharField(max_length=64, unique=True, db_index=True)
    group = models.ForeignKey('groups.EqubGroup', on_delete=models.CASCADE, related_name='payment_attempts')
    obligation = models.ForeignKey(
        'contributions.ContributionObligation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attempts'
    )
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payment_attempts')
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices)
    provider_name = models.CharField(max_length=100, default='TEST_TELEBIRR_ADAPTER')
    provider_reference = models.CharField(max_length=100, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='ETB')
    status = models.CharField(max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.INITIATED)
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True)
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payment_attempts'

    def __str__(self):
        return f"Attempt {self.internal_reference} [{self.status}]"


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt_number = models.CharField(max_length=64, unique=True, db_index=True)
    attempt = models.OneToOneField(
        PaymentAttempt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_payment'
    )
    group = models.ForeignKey('groups.EqubGroup', on_delete=models.CASCADE, related_name='payments')
    obligation = models.ForeignKey(
        'contributions.ContributionObligation',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='payments'
    )
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payments')
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='ETB')
    status = models.CharField(max_length=30, choices=PaymentStatus.choices, default=PaymentStatus.PENDING_VERIFICATION, db_index=True)
    settlement_status = models.CharField(max_length=30, choices=SettlementStatus.choices, default=SettlementStatus.NOT_APPLICABLE)
    provider_transaction_reference = models.CharField(max_length=120, unique=True, null=True, blank=True, db_index=True)
    
    # Specific fields for Method B (Cash)
    cash_receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_cash_entries'
    )
    cash_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_cash_entries'
    )
    
    # Specific fields for Method C (Bank / Mobile Transfer)
    transfer_reference = models.CharField(max_length=120, blank=True, db_index=True)
    transfer_evidence_file = models.FileField(upload_to='payment_evidence/', blank=True, null=True)
    
    # Verification audit
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['payer', 'status']),
            models.Index(fields=['payment_method', 'status']),
        ]

    def __str__(self):
        return f"Payment {self.receipt_number} - {self.amount} {self.currency} [{self.status}]"


class PaymentAllocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='allocations')
    obligation = models.ForeignKey(
        'contributions.ContributionObligation',
        on_delete=models.CASCADE,
        related_name='allocations'
    )
    amount_allocated = models.DecimalField(max_digits=12, decimal_places=2)
    allocated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment_allocations'

    def __str__(self):
        return f"{self.amount_allocated} ETB to Obligation {self.obligation.id}"


class ProviderEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider_name = models.CharField(max_length=60)
    event_id = models.CharField(max_length=150, db_index=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'provider_events'
        constraints = [
            models.UniqueConstraint(
                fields=['provider_name', 'event_id'],
                name='unique_provider_event_id'
            )
        ]

    def __str__(self):
        return f"{self.provider_name} - {self.event_id} (processed={self.processed})"


class ReconciliationException(models.Model):
    class ExceptionType(models.TextChoices):
        DUPLICATE_REFERENCE = 'DUPLICATE_REFERENCE', _('Duplicate Reference')
        AMOUNT_MISMATCH = 'AMOUNT_MISMATCH', _('Amount Mismatch')
        WRONG_BENEFICIARY = 'WRONG_BENEFICIARY', _('Wrong Beneficiary')
        UNIDENTIFIED_SENDER = 'UNIDENTIFIED_SENDER', _('Unidentified Sender')
        SUSPECTED_FRAUD = 'SUSPECTED_FRAUD', _('Suspected Fraud')
        OTHER = 'OTHER', _('Other Exception')

    class Status(models.TextChoices):
        OPEN = 'OPEN', _('Open')
        UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review')
        RESOLVED = 'RESOLVED', _('Resolved')
        DISMISSED = 'DISMISSED', _('Dismissed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        related_name='reconciliation_exceptions'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exceptions'
    )
    flagged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='flagged_reconciliation_exceptions'
    )
    exception_type = models.CharField(
        max_length=40,
        choices=ExceptionType.choices,
        default=ExceptionType.OTHER,
        db_index=True
    )
    reference_number = models.CharField(max_length=120, db_index=True)
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actual_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    description = models.TextField()
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True
    )
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reconciliation_exceptions'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reconciliation_exceptions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['exception_type', 'status']),
            models.Index(fields=['reference_number']),
        ]

    def __str__(self):
        return f"[{self.exception_type}] {self.reference_number} ({self.status}) - {self.group.name}"

