import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

class ContributionPeriod(models.Model):
    class PeriodStatus(models.TextChoices):
        UPCOMING = 'UPCOMING', _('Upcoming')
        OPEN = 'OPEN', _('Open')
        SETTLED = 'SETTLED', _('Settled')
        CLOSED = 'CLOSED', _('Closed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        related_name='periods'
    )
    period_number = models.PositiveIntegerField()
    start_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=PeriodStatus.choices,
        default=PeriodStatus.OPEN,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contribution_periods'
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'period_number'],
                name='unique_period_per_group'
            )
        ]
        ordering = ['group', 'period_number']

    def __str__(self):
        return f"{self.group.name} - Round {self.period_number} [{self.status}]"


class ContributionObligation(models.Model):
    class ObligationStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PARTIALLY_PAID = 'PARTIALLY_PAID', _('Partially Paid')
        PAID = 'PAID', _('Paid')
        OVERDUE = 'OVERDUE', _('Overdue')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(
        'groups.EqubGroup',
        on_delete=models.CASCADE,
        related_name='obligations'
    )
    membership = models.ForeignKey(
        'groups.GroupMembership',
        on_delete=models.PROTECT,
        related_name='obligations'
    )
    period = models.ForeignKey(
        ContributionPeriod,
        on_delete=models.CASCADE,
        related_name='obligations'
    )
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    currency = models.CharField(max_length=10, default='ETB')
    due_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=ObligationStatus.choices,
        default=ObligationStatus.PENDING,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contribution_obligations'
        constraints = [
            models.UniqueConstraint(
                fields=['group', 'membership', 'period'],
                name='unique_obligation_per_member_period'
            )
        ]
        indexes = [
            models.Index(fields=['group', 'status']),
            models.Index(fields=['membership', 'status']),
        ]

    def __str__(self):
        return f"Obligation: {self.membership.user.full_name} - Round {self.period.period_number} [{self.status}]"

    @property
    def remaining_amount(self) -> Decimal:
        rem = self.expected_amount - self.amount_paid
        return rem if rem > Decimal('0.00') else Decimal('0.00')
