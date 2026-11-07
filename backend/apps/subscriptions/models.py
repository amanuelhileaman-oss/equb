import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class SaasPlan(models.Model):
    class BillingCycle(models.TextChoices):
        MONTHLY = 'MONTHLY', _('Monthly')
        ANNUAL = 'ANNUAL', _('Annual')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    max_active_groups = models.PositiveIntegerField(default=1)
    price_etb = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    billing_cycle = models.CharField(max_length=15, choices=BillingCycle.choices, default=BillingCycle.MONTHLY)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'saas_plans'
        ordering = ['price_etb']

    def __str__(self):
        return f"{self.name} ({self.price_etb} ETB/{self.billing_cycle.lower()}) - Max {self.max_active_groups} groups"


class OrganizerSubscription(models.Model):
    class SubscriptionStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PENDING_PAYMENT = 'PENDING_PAYMENT', _('Pending Payment')
        ACTIVE = 'ACTIVE', _('Active')
        GRACE_PERIOD = 'GRACE_PERIOD', _('Grace Period')
        PAST_DUE = 'PAST_DUE', _('Past Due')
        SUSPENDED = 'SUSPENDED', _('Suspended')
        CANCELLED = 'CANCELLED', _('Cancelled')
        EXPIRED = 'EXPIRED', _('Expired')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        SaasPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING_PAYMENT,
        db_index=True
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)
    grace_period_days = models.PositiveIntegerField(default=7)

    class Meta:
        db_table = 'organizer_subscriptions'

    def __str__(self):
        return f"{self.organizer.full_name} -> {self.plan.name} [{self.status}]"


class SubscriptionInvoice(models.Model):
    class InvoiceStatus(models.TextChoices):
        UNPAID = 'UNPAID', _('Unpaid')
        PENDING = 'PENDING', _('Pending')
        PAID = 'PAID', _('Paid')
        FAILED = 'FAILED', _('Failed')
        CANCELLED = 'CANCELLED', _('Cancelled')
        REFUNDED = 'REFUNDED', _('Refunded')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subscription = models.ForeignKey(
        OrganizerSubscription,
        on_delete=models.CASCADE,
        related_name='invoices'
    )
    invoice_number = models.CharField(max_length=64, unique=True, db_index=True)
    amount_etb = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(
        max_length=15,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.UNPAID
    )
    payment_method = models.CharField(max_length=50, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=64, blank=True)
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subscription_invoices'

    def __str__(self):
        return f"Invoice {self.invoice_number} ({self.amount_etb} ETB) - {self.status}"
