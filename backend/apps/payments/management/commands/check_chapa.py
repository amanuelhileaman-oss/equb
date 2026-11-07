import hmac
import hashlib
import json
import uuid
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.payments.chapa import chapa_client, ChapaAPIError


class Command(BaseCommand):
    help = "Diagnose and verify Chapa payment gateway configuration and connectivity."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("   DIGITAL EQUB ETHIOPIA — CHAPA DIAGNOSTICS      "))
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))

        has_errors = False

        # 1. Environment & Settings Checks
        self.stdout.write("\n1. Checking Settings & Environment Configuration:")

        sec_key = getattr(settings, 'CHAPA_SECRET_KEY', '')
        pub_key = getattr(settings, 'CHAPA_PUBLIC_KEY', '')
        wh_sec = getattr(settings, 'CHAPA_WEBHOOK_SECRET', '')
        api_url = getattr(settings, 'CHAPA_API_URL', '')
        sandbox = getattr(settings, 'CHAPA_SANDBOX_MODE', True)

        if sec_key:
            masked_sec = sec_key[:10] + "..." + sec_key[-4:] if len(sec_key) > 14 else "***"
            self.stdout.write(self.style.SUCCESS(f"  [✓] CHAPA_SECRET_KEY: {masked_sec}"))
        else:
            self.stdout.write(self.style.ERROR("  [✗] CHAPA_SECRET_KEY is missing!"))
            has_errors = True

        if pub_key:
            masked_pub = pub_key[:10] + "..." + pub_key[-4:] if len(pub_key) > 14 else "***"
            self.stdout.write(self.style.SUCCESS(f"  [✓] CHAPA_PUBLIC_KEY: {masked_pub}"))
        else:
            self.stdout.write(self.style.WARNING("  [!] CHAPA_PUBLIC_KEY is missing or empty."))

        if wh_sec:
            self.stdout.write(self.style.SUCCESS(f"  [✓] CHAPA_WEBHOOK_SECRET: Configured"))
        else:
            self.stdout.write(self.style.WARNING("  [!] CHAPA_WEBHOOK_SECRET is empty (defaults used)."))

        self.stdout.write(self.style.SUCCESS(f"  [✓] CHAPA_API_URL: {api_url}"))
        self.stdout.write(self.style.SUCCESS(f"  [✓] CHAPA_SANDBOX_MODE: {sandbox}"))

        # 2. Test Transaction Initialization
        self.stdout.write("\n2. Testing Chapa Transaction Initiation:")
        test_ref = f"TEST-CHP-{uuid.uuid4().hex[:8].upper()}"
        try:
            init_res = chapa_client.initialize_transaction(
                amount=Decimal("150.00"),
                currency="ETB",
                email="diagnostics@digitalequb.et",
                first_name="Abebe",
                last_name="Tester",
                tx_ref=test_ref,
                callback_url="http://localhost:8000/api/v1/webhooks/chapa/",
                return_url="http://localhost:5173/?tx_ref=" + test_ref,
                phone_number="+251911223344",
                customization={"title": "Equb Check", "description": "Verification check"}
            )
            checkout_url = init_res.get('checkout_url', '')
            is_mock = init_res.get('is_sandbox', False)
            mode_tag = "(Test Sandbox Mode)" if is_mock else "(Live Chapa Gateway)"
            self.stdout.write(self.style.SUCCESS(f"  [✓] Transaction initialized successfully {mode_tag}"))
            self.stdout.write(f"      Reference: {test_ref}")
            self.stdout.write(f"      Checkout URL: {checkout_url}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [✗] Failed to initialize transaction: {e}"))
            has_errors = True

        # 3. Test Transaction Verification
        self.stdout.write("\n3. Testing Server-Side Verification Endpoint Logic:")
        try:
            ver_res = chapa_client.verify_transaction(test_ref)
            raw_status = ver_res.get('raw_status') or ver_res.get('status')
            self.stdout.write(self.style.SUCCESS(f"  [✓] Verification endpoint reachable"))
            self.stdout.write(f"      Status: {raw_status}")
            self.stdout.write(f"      Amount: {ver_res.get('amount')} {ver_res.get('currency', 'ETB')}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [✗] Verification check failed: {e}"))
            has_errors = True

        # 4. Test Cryptographic HMAC Webhook Signature
        self.stdout.write("\n4. Testing Webhook Cryptographic HMAC SHA256 Signature:")
        try:
            sample_payload = json.dumps({
                "event": "charge.success",
                "tx_ref": test_ref,
                "amount": "150.00",
                "currency": "ETB",
                "status": "success"
            }, separators=(',', ':')).encode('utf-8')

            signature = hmac.new(
                chapa_client.webhook_secret.encode('utf-8'),
                sample_payload,
                hashlib.sha256
            ).hexdigest()

            valid = chapa_client.verify_webhook_signature(sample_payload, signature)
            if valid:
                self.stdout.write(self.style.SUCCESS("  [✓] HMAC SHA256 signature generation and validation: PASS"))
            else:
                self.stdout.write(self.style.ERROR("  [✗] HMAC SHA256 signature verification failed."))
                has_errors = True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  [✗] Webhook verification error: {e}"))
            has_errors = True

        self.stdout.write(self.style.MIGRATE_HEADING("\n=================================================="))
        if not has_errors:
            self.stdout.write(self.style.SUCCESS("  RESULT: ALL CHAPA CONFIGURATION CHECKS PASSED! ✓"))
        else:
            self.stdout.write(self.style.ERROR("  RESULT: CONFIGURATION ISSUES DETECTED! ✗"))
        self.stdout.write(self.style.MIGRATE_HEADING("==================================================\n"))

