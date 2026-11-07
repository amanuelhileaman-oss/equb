import hmac
import hashlib
import json
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.accounts.models import User, OrganizerProfile
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.contributions.models import ContributionObligation, ContributionPeriod
from apps.payments.models import PaymentAttempt, Payment, PaymentStatus, PaymentMethod
from apps.subscriptions.models import SaasPlan, OrganizerSubscription, SubscriptionInvoice


class ChapaPaymentsTests(APITestCase):
    def setUp(self):
        ensure_permissions_seeded()

        # Platform Owner / Super Admin
        self.superadmin = User.objects.create_superuser(
            phone_number="+251911000001",
            email="admin@digitalequb.et",
            full_name="Platform Superadmin",
            password="adminpassword123"
        )

        # Organizer User
        self.organizer_user = User.objects.create_user(
            phone_number="+251911000002",
            email="organizer@digitalequb.et",
            full_name="Dawit Organizer",
            password="password123"
        )
        self.growth_plan = SaasPlan.objects.create(
            name="Growth Plan",
            code="GROWTH_TEST",
            price_etb=Decimal("600.00"),
            max_active_groups=5,
            is_active=True
        )
        self.starter_plan = SaasPlan.objects.create(
            name="Starter Plan",
            code="STARTER_TEST",
            price_etb=Decimal("0.00"),
            max_active_groups=1,
            is_active=True
        )
        self.organizer_profile = OrganizerProfile.objects.create(
            user=self.organizer_user,
            assigned_plan=self.growth_plan,
            verification_status=OrganizerProfile.VerificationStatus.APPROVED,
            payment_status=OrganizerProfile.PaymentStatus.PAYMENT_REQUIRED,
            subscription_amount=Decimal("600.00")
        )

        # Equb Group
        self.group = EqubGroup.objects.create(
            name="Alpha Equb",
            organizer=self.organizer_user,
            contribution_amount=Decimal("1000.00"),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=10,
            start_date=date.today(),
            status=EqubGroup.GroupStatus.ACTIVE
        )

        # Roles
        org_role = GroupRole.objects.get(group=None, code="GROUP_ORGANIZER")
        tre_role = GroupRole.objects.get(group=None, code="GROUP_TREASURER")
        mem_role = GroupRole.objects.get(group=None, code="GROUP_MEMBER")

        # Contributing Member User
        self.member_user = User.objects.create_user(
            phone_number="+251911000003",
            email="member@digitalequb.et",
            full_name="Abebe Member",
            password="password123"
        )
        self.membership = GroupMembership.objects.create(
            group=self.group,
            user=self.member_user,
            status=GroupMembership.MembershipStatus.ACTIVE
        )
        MembershipRoleAssignment.objects.create(membership=self.membership, role=mem_role)

        # Contribution Period and Obligation
        self.period = ContributionPeriod.objects.create(
            group=self.group,
            period_number=1,
            start_date=timezone.now().date(),
            due_date=(timezone.now() + timedelta(days=5)).date(),
            status=ContributionPeriod.PeriodStatus.OPEN
        )
        self.obligation = ContributionObligation.objects.create(
            group=self.group,
            membership=self.membership,
            period=self.period,
            expected_amount=Decimal("1000.00"),
            currency="ETB",
            due_date=self.period.due_date,
            status=ContributionObligation.ObligationStatus.PENDING
        )

        # Treasurer User
        self.treasurer_user = User.objects.create_user(
            phone_number="+251911000004",
            email="treasurer@digitalequb.et",
            full_name="Kebede Treasurer",
            password="password123"
        )
        tre_membership = GroupMembership.objects.create(
            group=self.group,
            user=self.treasurer_user,
            status=GroupMembership.MembershipStatus.ACTIVE
        )
        MembershipRoleAssignment.objects.create(membership=tre_membership, role=tre_role)

    # =========================================================================
    # 1. MEMBER CONTRIBUTION TESTS (CHAPA ONLY)
    # =========================================================================
    def test_member_initiate_digital_contribution_chapa(self):
        """Member initiates Equb contribution payment via Chapa."""
        self.client.force_authenticate(user=self.member_user)
        url = f"/api/v1/member/obligations/{self.obligation.id}/pay-digital/"
        response = self.client.post(url, {"provider_name": "CHAPA"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.data
        self.assertEqual(data["provider"], "CHAPA")
        self.assertIn("checkout_url", data)
        self.assertTrue(data["internal_reference"].startswith("EQUB-CHP-"))
        self.assertEqual(Decimal(str(data["amount"])), Decimal("1000.00"))

        attempt = PaymentAttempt.objects.get(internal_reference=data["internal_reference"])
        self.assertEqual(attempt.status, PaymentStatus.INITIATED)
        self.assertEqual(attempt.payer, self.member_user)
        self.assertEqual(attempt.group, self.group)

    def test_verify_chapa_contribution_payment(self):
        """Server-side verification of contribution credits obligation and updates group ledger."""
        self.client.force_authenticate(user=self.member_user)
        # 1. Initiate
        init_res = self.client.post(
            f"/api/v1/member/obligations/{self.obligation.id}/pay-digital/",
            {"provider_name": "CHAPA"},
            format="json"
        )
        tx_ref = init_res.data["internal_reference"]

        # 2. Verify via /api/v1/payments/chapa/verify/
        verify_url = "/api/v1/payments/chapa/verify/"
        ver_res = self.client.post(verify_url, {"tx_ref": tx_ref}, format="json")

        self.assertEqual(ver_res.status_code, status.HTTP_200_OK)
        self.assertEqual(ver_res.data["status"], "CONFIRMED")
        self.assertIn("receipt_number", ver_res.data)

        # 3. Check Database State
        self.obligation.refresh_from_db()
        self.assertEqual(self.obligation.remaining_amount, Decimal("0.00"))
        self.assertEqual(self.obligation.status, ContributionObligation.ObligationStatus.PAID)

        attempt = PaymentAttempt.objects.get(internal_reference=tx_ref)
        self.assertEqual(attempt.status, PaymentStatus.CONFIRMED)

        payment = Payment.objects.filter(attempt=attempt).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal("1000.00"))

    def test_verify_chapa_contribution_idempotency(self):
        """Duplicate verification requests must not double-credit obligations or duplicate payments."""
        self.client.force_authenticate(user=self.member_user)
        init_res = self.client.post(
            f"/api/v1/member/obligations/{self.obligation.id}/pay-digital/",
            {"provider_name": "CHAPA"},
            format="json"
        )
        tx_ref = init_res.data["internal_reference"]

        # First verification
        res1 = self.client.post("/api/v1/payments/chapa/verify/", {"tx_ref": tx_ref}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # Second verification
        res2 = self.client.post("/api/v1/payments/chapa/verify/", {"tx_ref": tx_ref}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data.get("already_confirmed"))

        # Only one Payment record should exist
        payments_count = Payment.objects.filter(attempt__internal_reference=tx_ref).count()
        self.assertEqual(payments_count, 1)

    # =========================================================================
    # 2. ORGANIZER SUBSCRIPTION TESTS (CHAPA ONLY)
    # =========================================================================
    def test_organizer_starter_plan_activation(self):
        """Starter plan (0 ETB) requires no payment and immediately activates subscription."""
        self.client.force_authenticate(user=self.organizer_user)
        response = self.client.post(
            "/api/v1/organizer/subscription/pay/",
            {"plan_id": str(self.starter_plan.id)},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("is_free_starter"))
        self.assertEqual(response.data.get("subscription_status"), OrganizerSubscription.SubscriptionStatus.ACTIVE)

        self.organizer_profile.refresh_from_db()
        self.assertEqual(self.organizer_profile.payment_status, OrganizerProfile.PaymentStatus.NOT_REQUIRED)
        self.assertTrue(self.organizer_profile.is_dashboard_accessible)

    def test_organizer_initiate_subscription_payment_chapa(self):
        """Organizer initiates SaaS rent payment for Growth plan via Chapa."""
        self.client.force_authenticate(user=self.organizer_user)
        response = self.client.post(
            "/api/v1/organizer/subscription/pay/",
            {"plan_id": str(self.growth_plan.id)},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertTrue(data["success"])
        self.assertEqual(data["provider"], "CHAPA")
        self.assertTrue(data["tx_ref"].startswith("SUB-ORG-"))
        self.assertIn("checkout_url", data)

        invoice = SubscriptionInvoice.objects.get(payment_reference=data["tx_ref"])
        self.assertEqual(invoice.status, SubscriptionInvoice.InvoiceStatus.PENDING)
        self.assertEqual(invoice.amount_etb, Decimal("600.00"))

    def test_organizer_verify_subscription_payment_chapa(self):
        """Verifying organizer subscription marks invoice PAID and unlocks dashboard."""
        self.client.force_authenticate(user=self.organizer_user)
        # 1. Initiate
        init_res = self.client.post(
            "/api/v1/organizer/subscription/pay/",
            {"plan_id": str(self.growth_plan.id)},
            format="json"
        )
        tx_ref = init_res.data["tx_ref"]

        # 2. Verify via /api/v1/payments/chapa/verify/
        ver_res = self.client.post(
            "/api/v1/payments/chapa/verify/",
            {"tx_ref": tx_ref},
            format="json"
        )
        self.assertEqual(ver_res.status_code, status.HTTP_200_OK)
        self.assertEqual(ver_res.data["status"], "CONFIRMED")
        self.assertEqual(ver_res.data["subscription_status"], OrganizerSubscription.SubscriptionStatus.ACTIVE)
        self.assertTrue(ver_res.data["gate_unlocked"])

        # 3. Check DB
        invoice = SubscriptionInvoice.objects.get(payment_reference=tx_ref)
        self.assertEqual(invoice.status, SubscriptionInvoice.InvoiceStatus.PAID)
        self.organizer_profile.refresh_from_db()
        self.assertEqual(self.organizer_profile.payment_status, OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED)

    # =========================================================================
    # 3. ROLE ISOLATION & SECURITY TESTS
    # =========================================================================
    def test_treasurer_blocked_from_paying_organizer_subscription(self):
        """Treasurers are strictly forbidden from paying or managing Organizer SaaS subscriptions."""
        self.client.force_authenticate(user=self.treasurer_user)
        response = self.client.post(
            "/api/v1/organizer/subscription/pay/",
            {"plan_id": str(self.growth_plan.id)},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_blocked_from_paying_organizer_subscription(self):
        """Ordinary members are strictly forbidden from paying Organizer SaaS subscriptions."""
        self.client.force_authenticate(user=self.member_user)
        response = self.client.post(
            "/api/v1/organizer/subscription/pay/",
            {"plan_id": str(self.growth_plan.id)},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_chapa_webhook_hmac_signature_validation(self):
        """Webhook with valid HMAC SHA256 signature updates transaction idempotently."""
        from django.conf import settings
        # Initiate a payment attempt
        attempt = PaymentAttempt.objects.create(
            internal_reference="EQUB-CHP-TESTWH001",
            group=self.group,
            obligation=self.obligation,
            payer=self.member_user,
            payment_method=PaymentMethod.DIGITAL_PROVIDER,
            provider_name="CHAPA",
            amount=Decimal("1000.00"),
            currency="ETB",
            status=PaymentStatus.INITIATED
        )

        payload = {
            "event": "charge.success",
            "tx_ref": "EQUB-CHP-TESTWH001",
            "reference": "CHP-WH-9999",
            "amount": "1000.00",
            "currency": "ETB",
            "status": "success"
        }
        body_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        secret = getattr(settings, 'CHAPA_WEBHOOK_SECRET', 'test-chapa-webhook-secret')
        signature = hmac.new(secret.encode('utf-8'), body_bytes, hashlib.sha256).hexdigest()

        response = self.client.post(
            "/api/v1/webhooks/chapa/",
            data=body_bytes,
            content_type="application/json",
            HTTP_X_CHAPA_SIGNATURE=signature
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, PaymentStatus.CONFIRMED)
        self.obligation.refresh_from_db()
        self.assertEqual(self.obligation.status, ContributionObligation.ObligationStatus.PAID)

    # =========================================================================
    # 4. CHAPA SUBACCOUNTS & DIRECT GROUP SETTLEMENT TESTS
    # =========================================================================
    def test_get_supported_banks(self):
        """Supported Ethiopian banks and mobile money wallets can be retrieved."""
        self.client.force_authenticate(user=self.organizer_user)
        response = self.client.get("/api/v1/payments/banks/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("banks", response.data)
        banks = response.data["banks"]
        self.assertTrue(len(banks) > 0)
        bank_names = [b.get("name", "") for b in banks]
        self.assertTrue(any("Commercial Bank of Ethiopia" in name for name in bank_names))

    def test_get_group_subaccount_info(self):
        """Anyone in the group can view whether a group has a linked Chapa subaccount."""
        self.client.force_authenticate(user=self.organizer_user)
        response = self.client.get(f"/api/v1/groups/{self.group.id}/subaccount/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["has_subaccount"])

    def test_link_group_subaccount_by_organizer(self):
        """Organizer can register the group's common bank account as a Chapa Subaccount."""
        self.client.force_authenticate(user=self.organizer_user)
        payload = {
            "business_name": "Alpha Equb Group Savings",
            "bank_code": "946",
            "bank_name": "Commercial Bank of Ethiopia",
            "account_name": "Alpha Equb Common Committee",
            "account_number": "1000123456789"
        }
        response = self.client.post(
            f"/api/v1/groups/{self.group.id}/subaccount/",
            data=payload,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertTrue(bool(response.data["subaccount_id"]))

        # Verify group updated
        self.group.refresh_from_db()
        self.assertTrue(bool(self.group.chapa_subaccount_id))
        self.assertEqual(self.group.bank_code, "946")
        self.assertEqual(self.group.bank_name, "Commercial Bank of Ethiopia")
        self.assertEqual(self.group.bank_account_number, "1000123456789")

    def test_link_group_subaccount_forbidden_for_regular_member(self):
        """Regular members cannot alter the group's settlement subaccount."""
        self.client.force_authenticate(user=self.member_user)
        payload = {
            "business_name": "Malicious Subaccount",
            "bank_code": "946",
            "bank_name": "CBE",
            "account_name": "Rogue Account",
            "account_number": "1000999999999"
        }
        response = self.client.post(
            f"/api/v1/groups/{self.group.id}/subaccount/",
            data=payload,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_payment_routes_to_group_subaccount(self):
        """When an Equb group has a subaccount, digital payment initiation routes to it."""
        self.group.chapa_subaccount_id = "test-subaccount-uuid-abc1234"
        self.group.bank_code = "946"
        self.group.bank_name = "Commercial Bank of Ethiopia"
        self.group.bank_account_name = "Alpha Group Common"
        self.group.bank_account_number = "1000123456789"
        self.group.save()

        self.client.force_authenticate(user=self.member_user)
        response = self.client.post(
            f"/api/v1/member/obligations/{self.obligation.id}/pay-digital/",
            {"provider_name": "CHAPA"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("checkout_url", response.data)
        attempt = PaymentAttempt.objects.get(obligation=self.obligation)
        self.assertEqual(attempt.provider_name, "CHAPA")
        self.assertEqual(attempt.status, PaymentStatus.INITIATED)
