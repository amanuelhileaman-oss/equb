import hmac
import hashlib
import json
from decimal import Decimal
from typing import Dict, Any
from django.conf import settings
from .chapa import chapa_client, ChapaAPIError


class BasePaymentAdapter:
    """Base interface for digital payment provider adapters."""
    provider_name: str = 'BASE_ADAPTER'
    is_live_ready: bool = False

    def initiate_payment(self, attempt) -> Dict[str, Any]:
        raise NotImplementedError

    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str = "") -> bool:
        raise NotImplementedError

    def parse_event(self, raw_payload: dict) -> Dict[str, Any]:
        raise NotImplementedError

    def verify_payment(self, tx_ref: str) -> Dict[str, Any]:
        raise NotImplementedError


class ChapaPaymentAdapter(BasePaymentAdapter):
    """
    Official Chapa Payment Gateway v2 Adapter for Digital Equb Ethiopia.
    Handles hosted checkout initiation, server-side transaction verification,
    and webhook processing.
    """
    provider_name = 'CHAPA'
    # Per Section 5.4, kept in test/sandbox mode until formal group settlement is certified.
    is_live_ready = False

    def initiate_payment(self, attempt) -> Dict[str, Any]:
        user = attempt.payer
        name_parts = (user.full_name or "Equb Member").split()
        first_name = name_parts[0] if name_parts else "Equb"
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "Member"

        backend_base = getattr(settings, 'BACKEND_BASE_URL', 'http://localhost:8000').rstrip('/')
        frontend_base = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:5173').rstrip('/')

        callback_url = f"{backend_base}/api/v1/webhooks/chapa/"
        return_url = f"{frontend_base}/?tab=contributions&payment_status=verifying&tx_ref={attempt.internal_reference}"

        customization = {
            "title": f"Equb: {attempt.group.name}"[:16],
            "description": f"Contribution: {attempt.group.name}"[:50]
        }
        meta = {
            "payment_purpose": "EQUB_CONTRIBUTION",
            "group_id": str(attempt.group_id),
            "obligation_id": str(attempt.obligation_id) if attempt.obligation_id else "",
            "member_id": str(attempt.payer_id),
            "attempt_id": str(attempt.id)
        }

        # Check if the Equb group has a designated Chapa Subaccount
        group = attempt.group
        subaccount_id = getattr(group, 'chapa_subaccount_id', '') or ''
        if not subaccount_id and hasattr(group, 'payment_destinations'):
            dest = group.payment_destinations.filter(is_active=True).exclude(chapa_subaccount_id='').first()
            if dest:
                subaccount_id = dest.chapa_subaccount_id

        res = chapa_client.initialize_transaction(
            amount=attempt.amount,
            currency=attempt.currency,
            email=user.email,
            first_name=first_name,
            last_name=last_name,
            tx_ref=attempt.internal_reference,
            callback_url=callback_url,
            return_url=return_url,
            phone_number=getattr(user, 'phone_number', '') or '',
            customization=customization,
            meta=meta,
            subaccount_id=subaccount_id or None
        )

        return {
            'provider': self.provider_name,
            'checkout_url': res.get('checkout_url'),
            'provider_reference': f"CHAPA-{attempt.internal_reference}",
            'tx_ref': attempt.internal_reference,
            'amount': str(attempt.amount),
            'currency': attempt.currency,
            'is_sandbox': res.get('is_sandbox', True),
            'instructions': "Redirecting to official Chapa hosted checkout..."
        }

    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str = "") -> bool:
        return chapa_client.verify_webhook_signature(payload, signature)

    def parse_event(self, raw_payload: dict) -> Dict[str, Any]:
        """Parses standard Chapa webhook payload."""
        # Chapa sends tx_ref, reference, amount, currency, status, meta
        tx_ref = raw_payload.get('tx_ref') or raw_payload.get('trx_ref')
        chapa_ref = raw_payload.get('reference') or raw_payload.get('chapa_reference', '')
        amt_raw = raw_payload.get('amount', '0.00')
        currency = (raw_payload.get('currency') or 'ETB').upper()
        status_raw = (raw_payload.get('status') or 'success').upper()

        return {
            'event_id': chapa_ref or f"evt_{tx_ref}",
            'internal_reference': tx_ref,
            'provider_reference': chapa_ref,
            'amount': Decimal(str(amt_raw)),
            'currency': currency,
            'status': 'SUCCESS' if status_raw in ('SUCCESS', 'PAID', 'COMPLETED') else status_raw,
            'raw_payload': raw_payload
        }

    def verify_payment(self, tx_ref: str) -> Dict[str, Any]:
        return chapa_client.verify_transaction(tx_ref)


class TestTelebirrAdapter(BasePaymentAdapter):
    """Retained for legacy test suite simulation compatibility."""
    provider_name = 'TEST_TELEBIRR_ADAPTER'
    is_live_ready = False

    def initiate_payment(self, attempt) -> Dict[str, Any]:
        return {
            'provider': self.provider_name,
            'checkout_url': f"http://localhost:5173/mock-telebirr-gateway?ref={attempt.internal_reference}&amount={attempt.amount}",
            'provider_reference': f"TB-{attempt.internal_reference}",
            'instructions': "Test Telebirr Adapter: Enter PIN to confirm payment in test mode.",
            'is_test_adapter': True
        }

    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str = "test-telebirr-secret") -> bool:
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_event(self, raw_payload: dict) -> Dict[str, Any]:
        return {
            'event_id': raw_payload.get('event_id'),
            'internal_reference': raw_payload.get('internal_reference'),
            'provider_reference': raw_payload.get('telebirr_transaction_id'),
            'amount': Decimal(str(raw_payload.get('amount'))),
            'currency': raw_payload.get('currency', 'ETB'),
            'status': raw_payload.get('status', 'SUCCESS')
        }

    def verify_payment(self, tx_ref: str) -> Dict[str, Any]:
        return {
            'status': 'success',
            'raw_status': 'SUCCESS',
            'tx_ref': tx_ref,
            'amount': Decimal('100.00'),
            'currency': 'ETB'
        }


class TestCbeBirrAdapter(BasePaymentAdapter):
    """Retained for legacy test suite simulation compatibility."""
    provider_name = 'TEST_CBE_BIRR_ADAPTER'
    is_live_ready = False

    def initiate_payment(self, attempt) -> Dict[str, Any]:
        return {
            'provider': self.provider_name,
            'checkout_url': f"http://localhost:5173/mock-cbe-gateway?ref={attempt.internal_reference}&amount={attempt.amount}",
            'provider_reference': f"CBE-{attempt.internal_reference}",
            'instructions': "Test CBE Birr Adapter: Enter USSD simulation code.",
            'is_test_adapter': True
        }

    def verify_webhook_signature(self, payload: bytes, signature: str, secret: str = "test-cbe-secret") -> bool:
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parse_event(self, raw_payload: dict) -> Dict[str, Any]:
        return {
            'event_id': raw_payload.get('event_id'),
            'internal_reference': raw_payload.get('internal_reference'),
            'provider_reference': raw_payload.get('cbe_reference'),
            'amount': Decimal(str(raw_payload.get('amount'))),
            'currency': raw_payload.get('currency', 'ETB'),
            'status': raw_payload.get('status', 'SUCCESS')
        }

    def verify_payment(self, tx_ref: str) -> Dict[str, Any]:
        return {
            'status': 'success',
            'raw_status': 'SUCCESS',
            'tx_ref': tx_ref,
            'amount': Decimal('100.00'),
            'currency': 'ETB'
        }


ADAPTER_REGISTRY = {
    'CHAPA': ChapaPaymentAdapter(),
    'TEST_TELEBIRR_ADAPTER': TestTelebirrAdapter(),
    'TEST_CBE_BIRR_ADAPTER': TestCbeBirrAdapter(),
}

def get_adapter(provider_name: str = 'CHAPA') -> BasePaymentAdapter:
    if not provider_name:
        return ADAPTER_REGISTRY['CHAPA']
    normalized = provider_name.strip().upper()
    if normalized in ('CHAPA', 'CHAPA_GATEWAY', 'CHAPA_ONLY', 'DEFAULT'):
        return ADAPTER_REGISTRY['CHAPA']
    if normalized in ('TELEBIRR', 'TEST_TELEBIRR', 'TEST_TELEBIRR_ADAPTER'):
        return ADAPTER_REGISTRY['TEST_TELEBIRR_ADAPTER']
    if normalized in ('CBE_BIRR', 'CBEBIRR', 'TEST_CBE_BIRR', 'TEST_CBE_BIRR_ADAPTER'):
        return ADAPTER_REGISTRY['TEST_CBE_BIRR_ADAPTER']
    # Default to Chapa as per instruction "CHAPA ONLY"
    return ADAPTER_REGISTRY['CHAPA']
