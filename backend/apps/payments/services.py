import uuid
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import (
    PaymentAttempt, Payment, PaymentAllocation, ProviderEvent,
    PaymentMethod, PaymentStatus, SettlementStatus, GroupPaymentDestination
)
from .adapters import get_adapter
from apps.contributions.models import ContributionObligation
from apps.ledger.services import record_contribution_ledger
from apps.authorization.services import has_group_permission

def generate_reference(prefix: str = "TXN") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


# ==========================================
# METHOD A: Digital Payment Workflow
# ==========================================

@transaction.atomic
def initiate_digital_payment(obligation: ContributionObligation, payer, provider_name: str = 'CHAPA', idempotency_key: str = None) -> dict:
    """
    Initializes an official Chapa hosted checkout payment session for an Equb contribution obligation.
    Uses exact database obligation remaining_amount to prevent client-side amount tampering.
    """
    if obligation.membership.user_id != payer.id:
        raise PermissionDenied("You can only initiate payment for your own contribution obligations.")

    if obligation.status == ContributionObligation.ObligationStatus.PAID:
        raise ValidationError("This obligation is already fully paid.")

    if idempotency_key:
        existing_attempt = PaymentAttempt.objects.filter(idempotency_key=idempotency_key).first()
        if existing_attempt:
            adapter = get_adapter(existing_attempt.provider_name)
            return adapter.initiate_payment(existing_attempt)

    amount = obligation.remaining_amount
    internal_ref = generate_reference("EQUB-CHP")

    attempt = PaymentAttempt.objects.create(
        internal_reference=internal_ref,
        group=obligation.group,
        obligation=obligation,
        payer=payer,
        payment_method=PaymentMethod.DIGITAL_PROVIDER,
        provider_name=provider_name or 'CHAPA',
        amount=amount,
        currency=obligation.currency,
        status=PaymentStatus.INITIATED,
        idempotency_key=idempotency_key
    )

    adapter = get_adapter(provider_name or 'CHAPA')
    result = adapter.initiate_payment(attempt)
    if 'provider_reference' in result:
        attempt.provider_reference = result['provider_reference']
        attempt.save(update_fields=['provider_reference'])

    result['internal_reference'] = internal_ref
    result['attempt_id'] = str(attempt.id)
    return result


@transaction.atomic
def verify_chapa_contribution_payment(tx_ref: str, payer=None) -> dict:
    """
    Server-side verification of an Equb group contribution payment with Chapa.
    Verifies amount, currency, group ownership, and idempotently credits the member's obligation.
    """
    attempt = PaymentAttempt.objects.filter(internal_reference=tx_ref).select_related('obligation', 'group', 'payer').first()
    if not attempt:
        raise ValidationError(f"No payment attempt found for reference '{tx_ref}'.")

    is_authorized = (
        not payer or
        payer.is_platform_admin or
        attempt.payer_id == payer.id or
        attempt.group.organizer_id == payer.id or
        has_group_permission(payer, attempt.group, 'payments:reconcile')
    )
    if not is_authorized:
        raise PermissionDenied("You are not authorized to verify payment attempts of another member.")

    # Idempotent return if already confirmed
    if attempt.status == PaymentStatus.CONFIRMED:
        existing_payment = Payment.objects.filter(attempt=attempt).first()
        receipt = existing_payment.receipt_number if existing_payment else f"RCP-{tx_ref}"
        return {
            'status': 'CONFIRMED',
            'receipt_number': receipt,
            'amount': str(attempt.amount),
            'currency': attempt.currency,
            'group_id': str(attempt.group_id),
            'group_name': attempt.group.name,
            'obligation_id': str(attempt.obligation_id) if attempt.obligation_id else None,
            'already_confirmed': True
        }

    # Verify directly with Chapa API
    adapter = get_adapter('CHAPA')
    verification = adapter.verify_payment(tx_ref)

    if verification.get('raw_status') != 'SUCCESS':
        attempt.status = PaymentStatus.FAILED
        attempt.save(update_fields=['status'])
        return {
            'status': 'FAILED',
            'reason': verification.get('raw_status', 'FAILED'),
            'tx_ref': tx_ref
        }

    # Verify expected amount and currency
    ver_amount = Decimal(str(verification['amount']))
    if ver_amount != attempt.amount or verification['currency'].upper() != attempt.currency.upper():
        raise ValidationError(
            f"Chapa payment amount or currency mismatch: expected {attempt.amount} {attempt.currency}, verified {ver_amount} {verification['currency']}."
        )

    # Mark attempt confirmed
    attempt.status = PaymentStatus.CONFIRMED
    attempt.completed_at = timezone.now()
    chapa_ref = verification.get('chapa_reference') or f"CHAPA-{tx_ref}"
    attempt.provider_reference = chapa_ref
    attempt.save(update_fields=['status', 'completed_at', 'provider_reference'])

    # Check if a Payment record for this attempt or provider reference already exists
    existing_payment = Payment.objects.filter(attempt=attempt).first() or (
        Payment.objects.filter(provider_transaction_reference=chapa_ref).first() if chapa_ref else None
    )
    if existing_payment:
        return {
            'status': 'CONFIRMED',
            'receipt_number': existing_payment.receipt_number,
            'amount': str(existing_payment.amount),
            'currency': existing_payment.currency,
            'group_id': str(attempt.group_id),
            'group_name': attempt.group.name,
            'obligation_id': str(attempt.obligation_id) if attempt.obligation_id else None,
            'already_confirmed': True
        }

    # Create confirmed payment record
    receipt_num = generate_reference("RCP-CHP")
    while Payment.objects.filter(receipt_number=receipt_num).exists():
        receipt_num = generate_reference("RCP-CHP")

    payment = Payment.objects.create(
        receipt_number=receipt_num,
        attempt=attempt,
        group=attempt.group,
        obligation=attempt.obligation,
        payer=attempt.payer,
        payment_method=PaymentMethod.DIGITAL_PROVIDER,
        amount=attempt.amount,
        currency=attempt.currency,
        status=PaymentStatus.CONFIRMED,
        settlement_status=SettlementStatus.AWAITING_SETTLEMENT,
        provider_transaction_reference=chapa_ref,
        verified_at=timezone.now(),
        notes="Verified directly with Chapa Payment Gateway"
    )

    if attempt.obligation:
        PaymentAllocation.objects.create(
            payment=payment,
            obligation=attempt.obligation,
            amount_allocated=payment.amount
        )
        ob = attempt.obligation
        ob.amount_paid += payment.amount
        if ob.amount_paid >= ob.expected_amount:
            ob.status = ContributionObligation.ObligationStatus.PAID
        else:
            ob.status = ContributionObligation.ObligationStatus.PARTIALLY_PAID
        ob.save()

    # Append to financial ledger
    record_contribution_ledger(payment)

    # In-app notification for member
    from apps.notifications.models import Notification
    Notification.objects.create(
        user=attempt.payer,
        title="Contribution Verified via Chapa",
        message=f"Your contribution payment of {payment.amount} {payment.currency} for {attempt.group.name} has been verified and confirmed. Receipt: {receipt_num}.",
        notification_type=Notification.NotificationType.PAYMENT_RECEIVED
    )

    return {
        'status': 'CONFIRMED',
        'receipt_number': receipt_num,
        'amount': str(payment.amount),
        'currency': payment.currency,
        'group_id': str(payment.group_id),
        'group_name': payment.group.name,
        'obligation_id': str(attempt.obligation_id) if attempt.obligation_id else None,
        'already_confirmed': False
    }


@transaction.atomic
def process_provider_webhook(provider_name: str, raw_payload: dict, raw_body_bytes: bytes, signature: str) -> dict:
    """
    Idempotent, cryptographically verified digital payment webhook processor.
    Protects against duplicate events, amount mismatches, and unauthorized status updates.
    """
    adapter = get_adapter(provider_name)
    
    # Verify cryptographic signature
    if not adapter.verify_webhook_signature(raw_body_bytes, signature):
        raise PermissionDenied("Invalid cryptographic webhook signature.")

    parsed = adapter.parse_event(raw_payload)
    event_id = parsed['event_id']

    # Strict idempotency check
    existing_event = ProviderEvent.objects.filter(provider_name=provider_name, event_id=event_id).first()
    if existing_event and existing_event.processed:
        return {'status': 'ALREADY_PROCESSED', 'event_id': event_id}

    provider_event, _ = ProviderEvent.objects.get_or_create(
        provider_name=provider_name,
        event_id=event_id,
        defaults={'payload': raw_payload, 'event_type': 'PAYMENT_STATUS_UPDATE'}
    )

    internal_ref = parsed['internal_reference']
    attempt = PaymentAttempt.objects.filter(internal_reference=internal_ref).first()
    if not attempt:
        # Check if reference belongs to an Organizer Subscription Invoice
        from apps.subscriptions.models import SubscriptionInvoice
        sub_invoice = SubscriptionInvoice.objects.filter(payment_reference=internal_ref).first()
        if sub_invoice:
            from apps.subscriptions.services import verify_chapa_subscription_payment
            res = verify_chapa_subscription_payment(internal_ref)
            provider_event.processed = True
            provider_event.save(update_fields=['processed'])
            return {
                'status': 'CONFIRMED',
                'type': 'ORGANIZER_SUBSCRIPTION',
                'invoice_number': sub_invoice.invoice_number,
                'amount': str(sub_invoice.amount_etb)
            }

        provider_event.processing_error = f"No contribution attempt or subscription invoice found for reference {internal_ref}"
        provider_event.save(update_fields=['processing_error'])
        raise ValidationError(f"Unknown internal payment reference: {internal_ref}")

    # Verify amount and currency
    if parsed['amount'] != attempt.amount or parsed['currency'] != attempt.currency:
        provider_event.processing_error = f"Amount or currency mismatch: expected {attempt.amount} {attempt.currency}, got {parsed['amount']} {parsed['currency']}"
        provider_event.save(update_fields=['processing_error'])
        raise ValidationError("Amount or currency does not match initial payment attempt.")

    if parsed['status'] == 'SUCCESS':
        attempt.status = PaymentStatus.CONFIRMED
        attempt.completed_at = timezone.now()
        attempt.provider_reference = parsed['provider_reference']
        attempt.save()

        # Create confirmed payment record
        receipt_num = generate_reference("RCP-DIG")
        payment = Payment.objects.create(
            receipt_number=receipt_num,
            attempt=attempt,
            group=attempt.group,
            obligation=attempt.obligation,
            payer=attempt.payer,
            payment_method=PaymentMethod.DIGITAL_PROVIDER,
            amount=attempt.amount,
            currency=attempt.currency,
            status=PaymentStatus.CONFIRMED,
            settlement_status=SettlementStatus.AWAITING_SETTLEMENT,
            provider_transaction_reference=parsed['provider_reference'],
            verified_at=timezone.now(),
            notes=f"Confirmed by digital provider adapter {provider_name}"
        )

        # Allocate to obligation and update balance
        if attempt.obligation:
            PaymentAllocation.objects.create(
                payment=payment,
                obligation=attempt.obligation,
                amount_allocated=payment.amount
            )
            ob = attempt.obligation
            ob.amount_paid += payment.amount
            if ob.amount_paid >= ob.expected_amount:
                ob.status = ContributionObligation.ObligationStatus.PAID
            else:
                ob.status = ContributionObligation.ObligationStatus.PARTIALLY_PAID
            ob.save()

        # Atomic append to double-entry financial ledger
        record_contribution_ledger(payment)

        provider_event.processed = True
        provider_event.save(update_fields=['processed'])
        return {'status': 'CONFIRMED', 'receipt_number': receipt_num, 'amount': str(payment.amount)}
    else:
        attempt.status = PaymentStatus.FAILED
        attempt.save()
        provider_event.processed = True
        provider_event.processing_error = f"Provider declared payment failed: {parsed['status']}"
        provider_event.save(update_fields=['processed', 'processing_error'])
        return {'status': 'FAILED', 'reason': parsed['status']}


# ==========================================
# METHOD B: Cash Paid to Treasurer Workflow
# ==========================================

@transaction.atomic
def record_cash_receipt(obligation: ContributionObligation, amount: Decimal, treasurer_user, receipt_number: str = None, notes: str = "", evidence_file=None) -> Payment:
    """
    Records in-person cash payment received by an authorized Treasurer.
    Respects group policy on second-person confirmation.
    """
    group = obligation.group
    if not has_group_permission(treasurer_user, group, 'cash_payments:record'):
        from apps.audit_app.security_monitor import record_and_block_security_violation
        record_and_block_security_violation(
            request=None,
            target_user=treasurer_user,
            attempted_operation="UNAUTHORIZED_CASH_RECEIPT_RECORDING",
            affected_resource=f"Group:{group.id}",
            security_rule_triggered="RULE-FIN-03: User lacks cash_payments:record permission.",
            risk_level="HIGH",
            group=group,
            details={"obligation_id": str(obligation.id), "amount": str(amount)}
        )

    if amount <= Decimal('0.00'):
        raise ValidationError("Payment amount must be greater than zero.")

    if amount > obligation.remaining_amount:
        raise ValidationError(f"Amount {amount} {obligation.currency} exceeds remaining obligation of {obligation.remaining_amount} {obligation.currency}.")

    receipt_num = receipt_number or generate_reference("RCP-CSH")
    if Payment.objects.filter(receipt_number=receipt_num).exists():
        raise ValidationError(f"Receipt number '{receipt_num}' is already in use.")

    needs_second_approval = group.require_cash_second_confirmation

    payment = Payment.objects.create(
        receipt_number=receipt_num,
        group=group,
        obligation=obligation,
        payer=obligation.membership.user,
        payment_method=PaymentMethod.CASH,
        amount=amount,
        currency=obligation.currency,
        status=PaymentStatus.PENDING_VERIFICATION if needs_second_approval else PaymentStatus.CONFIRMED,
        settlement_status=SettlementStatus.NOT_APPLICABLE,
        cash_receiver=treasurer_user,
        transfer_evidence_file=evidence_file,
        notes=notes,
        verified_by=None if needs_second_approval else treasurer_user,
        verified_at=None if needs_second_approval else timezone.now()
    )

    if not needs_second_approval:
        PaymentAllocation.objects.create(
            payment=payment,
            obligation=obligation,
            amount_allocated=amount
        )
        obligation.amount_paid += amount
        if obligation.amount_paid >= obligation.expected_amount:
            obligation.status = ContributionObligation.ObligationStatus.PAID
        else:
            obligation.status = ContributionObligation.ObligationStatus.PARTIALLY_PAID
        obligation.save()

        record_contribution_ledger(payment, posted_by=treasurer_user)

    return payment


@transaction.atomic
def confirm_cash_receipt(payment: Payment, confirming_user, notes: str = "") -> Payment:
    """
    Second-person independent confirmation for cash receipts when required by group rules.
    Enforces separation of duties: The confirming user cannot be the original cash receiver!
    """
    can_verify = (
        has_group_permission(confirming_user, payment.group, 'payments:reconcile') or
        has_group_permission(confirming_user, payment.group, 'group:manage')
    )
    if not can_verify:
        raise PermissionDenied("You do not have permission to confirm cash receipts.")

    # Separation of duties
    if confirming_user.id == payment.cash_receiver_id:
        raise PermissionDenied("Separation of duties: You cannot verify a cash receipt you personally received.")

    if payment.status != PaymentStatus.PENDING_VERIFICATION or payment.payment_method != PaymentMethod.CASH:
        raise ValidationError("Only pending cash entries can be confirmed.")

    payment.status = PaymentStatus.CONFIRMED
    payment.cash_confirmed_by = confirming_user
    payment.verified_by = confirming_user
    payment.verified_at = timezone.now()
    if notes:
        payment.notes = f"{payment.notes}\nConfirmation: {notes}".strip()
    payment.save()

    # Allocate & update obligation
    obligation = payment.obligation
    if obligation:
        PaymentAllocation.objects.create(
            payment=payment,
            obligation=obligation,
            amount_allocated=payment.amount
        )
        obligation.amount_paid += payment.amount
        if obligation.amount_paid >= obligation.expected_amount:
            obligation.status = ContributionObligation.ObligationStatus.PAID
        else:
            obligation.status = ContributionObligation.ObligationStatus.PARTIALLY_PAID
        obligation.save()

    record_contribution_ledger(payment, posted_by=confirming_user)
    return payment


# ==================================================
# METHOD C: Bank or Mobile Money Transfer Workflow
# ==================================================

@transaction.atomic
def submit_bank_transfer(obligation: ContributionObligation, member_user, transfer_reference: str, amount: Decimal, destination: GroupPaymentDestination = None, evidence_file=None, notes: str = "") -> Payment:
    """
    Member submits bank / Telebirr direct transfer evidence for Treasurer reconciliation.
    """
    if obligation.membership.user_id != member_user.id:
        raise PermissionDenied("You can only submit transfers for your own obligations.")

    if not transfer_reference or not transfer_reference.strip():
        raise ValidationError("A bank transfer or mobile transaction reference is required.")

    transfer_ref = transfer_reference.strip()
    # Check for duplicate transfer reference across existing confirmed payments
    if Payment.objects.filter(transfer_reference=transfer_ref, status=PaymentStatus.CONFIRMED).exists():
        raise ValidationError("This transfer reference has already been verified and reconciled.")

    receipt_num = generate_reference("RCP-TRF")

    payment = Payment.objects.create(
        receipt_number=receipt_num,
        group=obligation.group,
        obligation=obligation,
        payer=member_user,
        payment_method=PaymentMethod.BANK_TRANSFER,
        amount=amount,
        currency=obligation.currency,
        status=PaymentStatus.PENDING_VERIFICATION,
        settlement_status=SettlementStatus.AWAITING_SETTLEMENT,
        transfer_reference=transfer_ref,
        transfer_evidence_file=evidence_file,
        notes=notes
    )
    return payment


@transaction.atomic
def reconcile_bank_transfer(payment: Payment, treasurer_user, decision: str, notes: str = "") -> Payment:
    """
    Authorized Treasurer reconciles a bank transfer against actual group account records.
    """
    if not has_group_permission(treasurer_user, payment.group, 'payments:reconcile'):
        raise PermissionDenied("You do not have permission to reconcile bank transfers in this group.")

    if payment.status != PaymentStatus.PENDING_VERIFICATION:
        raise ValidationError(f"Payment is not in pending verification state (currently '{payment.status}').")

    if decision == 'CONFIRM':
        # Check duplicate reference again
        if payment.transfer_reference and Payment.objects.filter(
            transfer_reference=payment.transfer_reference,
            status=PaymentStatus.CONFIRMED
        ).exclude(id=payment.id).exists():
            raise ValidationError(f"Transfer reference '{payment.transfer_reference}' has already been matched to another confirmed payment.")

        payment.status = PaymentStatus.CONFIRMED
        payment.settlement_status = SettlementStatus.SETTLED
        payment.verified_by = treasurer_user
        payment.verified_at = timezone.now()
        if notes:
            payment.notes = f"{payment.notes}\nReconciled: {notes}".strip()
        payment.save()

        obligation = payment.obligation
        if obligation:
            PaymentAllocation.objects.create(
                payment=payment,
                obligation=obligation,
                amount_allocated=payment.amount
            )
            obligation.amount_paid += payment.amount
            if obligation.amount_paid >= obligation.expected_amount:
                obligation.status = ContributionObligation.ObligationStatus.PAID
            else:
                obligation.status = ContributionObligation.ObligationStatus.PARTIALLY_PAID
            obligation.save()

        record_contribution_ledger(payment, posted_by=treasurer_user)
    elif decision == 'REJECT':
        payment.status = PaymentStatus.FAILED
        if notes:
            payment.notes = f"{payment.notes}\nRejected reconciliation: {notes}".strip()
        payment.save()
    else:
        raise ValidationError(f"Invalid reconciliation decision '{decision}'. Expected 'CONFIRM' or 'REJECT'.")

    return payment
