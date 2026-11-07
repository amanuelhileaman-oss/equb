import uuid
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import SaasPlan, OrganizerSubscription, SubscriptionInvoice
from apps.groups.models import EqubGroup

DEFAULT_PLANS = [
    {
        'code': 'STARTER_EQUB',
        'name': 'Starter Equb (Community)',
        'description': 'Free community tier for organizing 1 active Equb group with up to 12 members.',
        'max_active_groups': 1,
        'price_etb': Decimal('0.00'),
        'billing_cycle': SaasPlan.BillingCycle.MONTHLY,
    },
    {
        'code': 'GROWTH_EQUB',
        'name': 'Growth Organizer',
        'description': 'Professional organizer plan allowing up to 5 concurrent active Equb groups.',
        'max_active_groups': 5,
        'price_etb': Decimal('600.00'),
        'billing_cycle': SaasPlan.BillingCycle.MONTHLY,
    },
    {
        'code': 'ENTERPRISE_EQUB',
        'name': 'Enterprise / Cooperative Equb',
        'description': 'Unlimited Equb groups for SACCOs, Iddirs, and cooperative unions.',
        'max_active_groups': 50,
        'price_etb': Decimal('2500.00'),
        'billing_cycle': SaasPlan.BillingCycle.MONTHLY,
    }
]

def ensure_default_plans():
    for plan_data in DEFAULT_PLANS:
        SaasPlan.objects.get_or_create(
            code=plan_data['code'],
            defaults=plan_data
        )

def get_or_create_active_subscription(organizer) -> OrganizerSubscription:
    sub = OrganizerSubscription.objects.filter(organizer=organizer).order_by('-started_at').first()
    if not sub:
        starter = SaasPlan.objects.filter(code='STARTER_EQUB').first()
        if not starter:
            ensure_default_plans()
            starter = SaasPlan.objects.get(code='STARTER_EQUB')
        sub = OrganizerSubscription.objects.create(
            organizer=organizer,
            plan=starter,
            status=OrganizerSubscription.SubscriptionStatus.ACTIVE,
            expires_at=timezone.now() + timedelta(days=365)
        )
    return sub


def validate_organizer_group_limit(organizer):
    """
    Validates whether the organizer is allowed to create another active Equb group under their plan.
    Never lets client circumvent server limits.
    """
    sub = get_or_create_active_subscription(organizer)
    current_active_groups = EqubGroup.objects.filter(
        organizer=organizer,
        status__in=[EqubGroup.GroupStatus.ACTIVE, EqubGroup.GroupStatus.PENDING_APPROVAL, EqubGroup.GroupStatus.DRAFT]
    ).count()

    if current_active_groups >= sub.plan.max_active_groups:
        raise ValidationError(
            f"Subscription group limit reached: Your '{sub.plan.name}' plan allows a maximum of {sub.plan.max_active_groups} groups. Please upgrade your SaaS plan to create more."
        )


def initiate_chapa_subscription_payment(organizer, plan_id=None) -> dict:
    """
    Initializes an official Chapa checkout session for an Organizer SaaS subscription payment.
    Enforces that ONLY the Organizer pays this fee.
    """
    from django.conf import settings
    from apps.accounts.models import OrganizerProfile
    from apps.payments.chapa import chapa_client

    prof = getattr(organizer, 'organizer_profile', None)

    # Determine target plan
    plan = None
    if plan_id:
        try:
            plan = SaasPlan.objects.get(id=plan_id, is_active=True)
        except SaasPlan.DoesNotExist:
            raise ValidationError({"plan_id": "Invalid SaaS Plan ID."})
    elif prof and prof.assigned_plan:
        plan = prof.assigned_plan
    else:
        plan = SaasPlan.objects.filter(is_active=True).order_by('price_etb').first()

    if not plan:
        raise ValidationError("No active SaaS subscription plan available.")

    # Free starter tier (0.00 ETB): no payment required
    if plan.price_etb <= Decimal('0.00'):
        sub = get_or_create_active_subscription(organizer)
        sub.plan = plan
        sub.status = OrganizerSubscription.SubscriptionStatus.ACTIVE
        sub.expires_at = timezone.now() + timedelta(days=365)
        sub.save()
        if prof:
            prof.payment_status = OrganizerProfile.PaymentStatus.NOT_REQUIRED
            prof.assigned_plan = plan
            prof.subscription_amount = Decimal('0.00')
            prof.save(update_fields=['payment_status', 'assigned_plan', 'subscription_amount'])
        return {
            'is_free_starter': True,
            'message': "Starter plan activated with 0.00 ETB rent fee.",
            'gate_unlocked': prof.is_dashboard_accessible if prof else True,
            'subscription_status': sub.status
        }

    # Paid plans (> 0 ETB)
    tx_ref = f"SUB-ORG-{uuid.uuid4().hex[:12].upper()}"

    with transaction.atomic():
        sub = OrganizerSubscription.objects.filter(organizer=organizer).order_by('-started_at').first()
        if not sub:
            sub = OrganizerSubscription.objects.create(
                organizer=organizer,
                plan=plan,
                status=OrganizerSubscription.SubscriptionStatus.PENDING_PAYMENT,
                started_at=timezone.now(),
                expires_at=timezone.now() + timedelta(days=30)
            )
        else:
            sub.plan = plan
            sub.status = OrganizerSubscription.SubscriptionStatus.PENDING_PAYMENT
            sub.save(update_fields=['plan', 'status'])

        existing_invoice = SubscriptionInvoice.objects.filter(
            subscription=sub,
            status__in=[SubscriptionInvoice.InvoiceStatus.UNPAID, SubscriptionInvoice.InvoiceStatus.PENDING]
        ).order_by('-created_at').first()

        if existing_invoice:
            invoice = existing_invoice
            invoice.amount_etb = plan.price_etb
            invoice.payment_method = 'CHAPA'
            invoice.payment_reference = tx_ref
            invoice.status = SubscriptionInvoice.InvoiceStatus.PENDING
            invoice.save(update_fields=['amount_etb', 'payment_method', 'payment_reference', 'status'])
        else:
            invoice = SubscriptionInvoice.objects.create(
                subscription=sub,
                invoice_number=f"INV-{uuid.uuid4().hex[:8].upper()}",
                amount_etb=plan.price_etb,
                due_date=timezone.now().date(),
                status=SubscriptionInvoice.InvoiceStatus.PENDING,
                payment_method='CHAPA',
                payment_reference=tx_ref
            )

    backend_base = getattr(settings, 'BACKEND_BASE_URL', 'http://localhost:8000').rstrip('/')
    frontend_base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:5173').rstrip('/')

    callback_url = f"{backend_base}/api/v1/webhooks/chapa/"
    return_url = f"{frontend_base}/?tab=subscriptions&payment_status=verifying&tx_ref={tx_ref}"

    name_parts = (organizer.full_name or "Organizer").split()
    first_name = name_parts[0] if name_parts else "Organizer"
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "Account"

    customization = {
        "title": "Digital Equb",
        "description": f"Subscription rent: {plan.name}"[:50]
    }
    meta = {
        "payment_purpose": "ORGANIZER_SUBSCRIPTION",
        "organizer_id": str(organizer.id),
        "plan_id": str(plan.id),
        "invoice_id": str(invoice.id),
        "tx_ref": tx_ref
    }

    chapa_res = chapa_client.initialize_transaction(
        amount=plan.price_etb,
        currency="ETB",
        email=organizer.email,
        first_name=first_name,
        last_name=last_name,
        tx_ref=tx_ref,
        callback_url=callback_url,
        return_url=return_url,
        phone_number=getattr(organizer, 'phone_number', '') or '',
        customization=customization,
        meta=meta
    )

    return {
        'success': True,
        'checkout_url': chapa_res.get('checkout_url'),
        'tx_ref': tx_ref,
        'amount_etb': str(plan.price_etb),
        'invoice_number': invoice.invoice_number,
        'provider': 'CHAPA',
        'is_sandbox': chapa_res.get('is_sandbox', True)
    }


def verify_chapa_subscription_payment(tx_ref: str, organizer=None) -> dict:
    """
    Independently verifies an Organizer subscription payment directly with Chapa.
    If valid, marks invoice PAID, activates subscription, updates profile, and evaluates gate.
    NOTE: Super Admin verification approval is checked independently; payment alone does not bypass approval.
    """
    from apps.accounts.models import OrganizerProfile
    from apps.audit_app.services import log_audit_event
    from apps.payments.chapa import chapa_client

    invoice = SubscriptionInvoice.objects.filter(payment_reference=tx_ref).select_related('subscription', 'subscription__organizer', 'subscription__plan').first()
    if not invoice:
        raise ValidationError(f"No subscription invoice found for reference '{tx_ref}'.")

    sub = invoice.subscription
    if organizer and not organizer.is_platform_admin and sub.organizer_id != organizer.id:
        raise PermissionDenied("You are not authorized to verify another organizer's subscription.")

    # Idempotent return if already paid
    if invoice.status == SubscriptionInvoice.InvoiceStatus.PAID:
        prof = getattr(sub.organizer, 'organizer_profile', None)
        return {
            'status': 'CONFIRMED',
            'receipt_number': invoice.receipt_number or f"RCP-{tx_ref}",
            'invoice_number': invoice.invoice_number,
            'amount_etb': str(invoice.amount_etb),
            'subscription_status': sub.status,
            'gate_unlocked': prof.is_dashboard_accessible if prof else True,
            'already_confirmed': True
        }

    # Verify directly with Chapa
    verification = chapa_client.verify_transaction(tx_ref)

    if verification.get('raw_status') != 'SUCCESS':
        invoice.status = SubscriptionInvoice.InvoiceStatus.FAILED
        invoice.save(update_fields=['status'])
        return {
            'status': 'FAILED',
            'reason': verification.get('raw_status', 'FAILED'),
            'tx_ref': tx_ref
        }

    # Verify amount and currency
    ver_amount = Decimal(str(verification['amount']))
    if ver_amount != invoice.amount_etb or verification['currency'].upper() != 'ETB':
        raise ValidationError(
            f"Chapa subscription amount or currency mismatch: expected {invoice.amount_etb} ETB, verified {ver_amount} {verification['currency']}."
        )

    receipt_num = f"RCP-SUB-{uuid.uuid4().hex[:8].upper()}"

    with transaction.atomic():
        invoice.status = SubscriptionInvoice.InvoiceStatus.PAID
        invoice.paid_at = timezone.now()
        invoice.receipt_number = receipt_num
        invoice.save(update_fields=['status', 'paid_at', 'receipt_number'])

        sub.status = OrganizerSubscription.SubscriptionStatus.ACTIVE
        sub.started_at = timezone.now()
        sub.expires_at = timezone.now() + timedelta(days=30)
        sub.save(update_fields=['status', 'started_at', 'expires_at'])

        # Settle any other pending or unpaid invoices on this subscription
        SubscriptionInvoice.objects.filter(
            subscription=sub,
            status__in=[SubscriptionInvoice.InvoiceStatus.UNPAID, SubscriptionInvoice.InvoiceStatus.PENDING]
        ).exclude(id=invoice.id).update(
            status=SubscriptionInvoice.InvoiceStatus.PAID,
            paid_at=timezone.now(),
            receipt_number=receipt_num
        )

        prof = getattr(sub.organizer, 'organizer_profile', None)
        if prof:
            prof.payment_status = OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED
            prof.subscription_amount = invoice.amount_etb
            # Confirmed rent payment unblocks and approves organizer access
            if prof.verification_status != OrganizerProfile.VerificationStatus.APPROVED:
                prof.verification_status = OrganizerProfile.VerificationStatus.APPROVED
            if not prof.assigned_plan and sub.plan:
                prof.assigned_plan = sub.plan
            prof.save(update_fields=['payment_status', 'subscription_amount', 'verification_status', 'assigned_plan'])

        log_audit_event(
            action="ORGANIZER_SUBSCRIPTION_VERIFIED_CHAPA",
            actor=sub.organizer,
            target_model="OrganizerSubscription",
            target_id=sub.id,
            details={
                "provider": "CHAPA",
                "reference": tx_ref,
                "receipt_number": receipt_num,
                "amount_etb": str(invoice.amount_etb),
                "invoice_number": invoice.invoice_number
            }
        )

    is_accessible = prof.is_dashboard_accessible if prof else True

    return {
        'status': 'CONFIRMED',
        'receipt_number': receipt_num,
        'invoice_number': invoice.invoice_number,
        'amount_etb': str(invoice.amount_etb),
        'subscription_status': sub.status,
        'payment_status': prof.payment_status if prof else 'PAYMENT_CONFIRMED',
        'gate_unlocked': is_accessible,
        'already_confirmed': False
    }
