from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q
from .models import LedgerEntry

def get_group_available_funds(group) -> Decimal:
    """
    Computes verified group fund balance from authoritative ledger records.
    Credits (Contributions in) minus Debits (Payouts disbursed).
    Never uses floating-point arithmetic.
    """
    totals = LedgerEntry.objects.filter(group=group).aggregate(
        total_credits=Sum('amount', filter=Q(direction=LedgerEntry.Direction.CREDIT)),
        total_debits=Sum('amount', filter=Q(direction=LedgerEntry.Direction.DEBIT))
    )
    credits = totals['total_credits'] or Decimal('0.00')
    debits = totals['total_debits'] or Decimal('0.00')
    return credits - debits


@transaction.atomic
def record_contribution_ledger(payment, posted_by=None) -> LedgerEntry:
    """
    Appends a CREDIT ledger entry when a contribution is verified & confirmed.
    """
    return LedgerEntry.objects.create(
        group=payment.group,
        entry_type=LedgerEntry.EntryType.CONTRIBUTION_RECEIVED,
        direction=LedgerEntry.Direction.CREDIT,
        amount=payment.amount,
        currency=payment.currency,
        payment=payment,
        posted_by=posted_by or payment.verified_by,
        reason=f"Verified contribution receipt {payment.receipt_number} via {payment.payment_method}"
    )


@transaction.atomic
def record_payout_ledger(payout, posted_by=None) -> LedgerEntry:
    """
    Appends a DEBIT ledger entry when a payout is executed.
    """
    return LedgerEntry.objects.create(
        group=payout.group,
        entry_type=LedgerEntry.EntryType.PAYOUT_DISBURSED,
        direction=LedgerEntry.Direction.DEBIT,
        amount=payout.amount,
        currency=payout.currency,
        payout=payout,
        posted_by=posted_by or payout.executed_by,
        reason=f"Executed payout disbursement for {payout.recipient_membership.user.full_name} (Round {payout.period.period_number if payout.period else 'N/A'})"
    )
