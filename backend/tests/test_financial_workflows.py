import hmac
import hashlib
import json
import pytest
from datetime import date, timedelta
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.contributions.models import ContributionPeriod, ContributionObligation
from apps.payments.models import Payment, PaymentStatus, PaymentMethod
from apps.payouts.models import Payout, PayoutStatus
from apps.payouts.services import request_payout, approve_payout, execute_payout
from apps.ledger.models import LedgerEntry
from apps.ledger.services import get_group_available_funds

@pytest.mark.django_db
class TestFinancialWorkflows:
    @pytest.fixture(autouse=True)
    def setup(self):
        ensure_permissions_seeded()
        self.client = APIClient()

        self.organizer = User.objects.create_user(email="org_fin@digitalequb.et", password="Password123!", full_name="Organizer Dawit")
        self.treasurer = User.objects.create_user(email="tre_fin@digitalequb.et", password="Password123!", full_name="Treasurer Bethlehem")
        self.member1 = User.objects.create_user(email="m1_fin@digitalequb.et", password="Password123!", full_name="Member Chala")

        self.group = EqubGroup.objects.create(
            name="Financial Test Group",
            organizer=self.organizer,
            status=EqubGroup.GroupStatus.ACTIVE,
            currency="ETB",
            contribution_amount=Decimal("1000.00"),
            start_date=date.today(),
            require_cash_second_confirmation=True
        )

        org_role = GroupRole.objects.get(group=None, code="GROUP_ORGANIZER")
        tre_role = GroupRole.objects.get(group=None, code="GROUP_TREASURER")
        mem_role = GroupRole.objects.get(group=None, code="GROUP_MEMBER")

        # Memberships
        self.m_org = GroupMembership.objects.create(group=self.group, user=self.organizer, status=GroupMembership.MembershipStatus.ACTIVE)
        MembershipRoleAssignment.objects.create(membership=self.m_org, role=org_role)

        self.m_tre = GroupMembership.objects.create(group=self.group, user=self.treasurer, status=GroupMembership.MembershipStatus.ACTIVE)
        MembershipRoleAssignment.objects.create(membership=self.m_tre, role=tre_role)

        self.m_m1 = GroupMembership.objects.create(group=self.group, user=self.member1, status=GroupMembership.MembershipStatus.ACTIVE)
        MembershipRoleAssignment.objects.create(membership=self.m_m1, role=mem_role)

        self.period = ContributionPeriod.objects.create(
            group=self.group,
            period_number=1,
            start_date=date.today(),
            due_date=date.today() + timedelta(days=7),
            status=ContributionPeriod.PeriodStatus.OPEN
        )

        self.ob1 = ContributionObligation.objects.create(
            group=self.group,
            membership=self.m_m1,
            period=self.period,
            expected_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=7),
            status=ContributionObligation.ObligationStatus.PENDING
        )

    def test_method_a_digital_payment_and_webhook_idempotency(self):
        # 1. Initiate digital payment
        self.client.force_authenticate(user=self.member1)
        res = self.client.post(f"/api/v1/member/obligations/{self.ob1.id}/pay-digital/", {
            "provider_name": "TEST_TELEBIRR_ADAPTER"
        }, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        internal_ref = res.data["internal_reference"]

        # 2. Simulate cryptographic Telebirr webhook
        webhook_payload = {
            "event_id": "EVT-1001",
            "internal_reference": internal_ref,
            "telebirr_transaction_id": "TB-TX-998877",
            "amount": "1000.00",
            "currency": "ETB",
            "status": "SUCCESS"
        }
        body_bytes = json.dumps(webhook_payload).encode()
        sig = hmac.new("test-telebirr-secret".encode(), body_bytes, hashlib.sha256).hexdigest()

        # Send webhook
        webhook_client = APIClient()
        wh_res = webhook_client.post(
            "/api/v1/webhooks/TEST_TELEBIRR_ADAPTER/",
            data=body_bytes,
            content_type="application/json",
            HTTP_X_SIGNATURE=sig
        )
        assert wh_res.status_code == status.HTTP_200_OK
        assert wh_res.data["status"] == "CONFIRMED"

        # Verify obligation updated and ledger entry created
        self.ob1.refresh_from_db()
        assert self.ob1.status == ContributionObligation.ObligationStatus.PAID
        assert self.ob1.amount_paid == Decimal("1000.00")
        assert LedgerEntry.objects.filter(group=self.group, direction=LedgerEntry.Direction.CREDIT).count() == 1

        # 3. Test Webhook Idempotency: Duplicate delivery must NOT create duplicate financial entries
        wh_res_dup = webhook_client.post(
            "/api/v1/webhooks/TEST_TELEBIRR_ADAPTER/",
            data=body_bytes,
            content_type="application/json",
            HTTP_X_SIGNATURE=sig
        )
        assert wh_res_dup.status_code == status.HTTP_200_OK
        assert wh_res_dup.data["status"] == "ALREADY_PROCESSED"
        assert LedgerEntry.objects.filter(group=self.group, direction=LedgerEntry.Direction.CREDIT).count() == 1

    def test_method_b_cash_dual_confirmation_and_separation_of_duties(self):
        # 1. Treasurer records cash receipt
        self.client.force_authenticate(user=self.treasurer)
        res = self.client.post(f"/api/v1/groups/{self.group.id}/cash-receipts/", {
            "obligation_id": str(self.ob1.id),
            "amount": "1000.00",
            "receipt_number": "RCP-CSH-001"
        }, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        payment_id = res.data["id"]
        # Because group has require_cash_second_confirmation=True, it starts as PENDING_VERIFICATION
        payment = Payment.objects.get(id=payment_id)
        assert payment.status == PaymentStatus.PENDING_VERIFICATION

        # 2. Treasurer attempts to confirm their own receipt -> must be REJECTED (Separation of duties)
        confirm_res = self.client.post(f"/api/v1/payments/{payment_id}/confirm-cash/", {}, format="json")
        assert confirm_res.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

        # 3. Independent person (Organizer with reconcile permission) confirms cash
        self.client.force_authenticate(user=self.organizer)
        confirm_res = self.client.post(f"/api/v1/payments/{payment_id}/confirm-cash/", {
            "notes": "Verified cash received in safe"
        }, format="json")
        assert confirm_res.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.status == PaymentStatus.CONFIRMED
        assert payment.cash_confirmed_by == self.organizer
        assert LedgerEntry.objects.filter(payment=payment, direction=LedgerEntry.Direction.CREDIT).exists()

    def test_payout_insufficient_funds_blocked_and_execution(self):
        # 1. Payout requested when available balance is 0 ETB
        self.client.force_authenticate(user=self.organizer)
        res = self.client.post(f"/api/v1/groups/{self.group.id}/payouts/", {
            "recipient_membership_id": str(self.m_m1.id),
            "amount": "1000.00"
        }, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        payout_id = res.data["id"]
        payout = Payout.objects.get(id=payout_id)
        assert payout.status == PayoutStatus.BLOCKED_INSUFFICIENT_FUNDS

        # 2. Seed verified funds into the group ledger
        LedgerEntry.objects.create(
            group=self.group,
            entry_type=LedgerEntry.EntryType.CONTRIBUTION_RECEIVED,
            direction=LedgerEntry.Direction.CREDIT,
            amount=Decimal("5000.00"),
            currency="ETB",
            reason="Initial pool deposit"
        )
        assert get_group_available_funds(self.group) == Decimal("5000.00")

        # 3. Create a valid payout request now that funds exist
        payout2 = request_payout(
            group=self.group,
            recipient_membership=self.m_m1,
            requesting_user=self.organizer,
            amount=Decimal("2000.00")
        )
        assert payout2.status == PayoutStatus.PENDING_APPROVAL

        # 4. Requester (Organizer) attempts to self-approve -> must be REJECTED (Separation of duties)
        self.client.force_authenticate(user=self.organizer)
        approve_res = self.client.post(f"/api/v1/payouts/{payout2.id}/approve/", {
            "decision": "APPROVED"
        }, format="json")
        assert approve_res.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST]

        # 5. Independent approver approves
        # Add payouts:approve permission to treasurer role
        tre_role = GroupRole.objects.get(group=None, code="GROUP_TREASURER")
        from apps.authorization.models import PermissionCatalog
        perm = PermissionCatalog.objects.get(codename="payouts:approve")
        tre_role.permissions.add(perm)

        self.client.force_authenticate(user=self.treasurer)
        approve_res = self.client.post(f"/api/v1/payouts/{payout2.id}/approve/", {
            "decision": "APPROVED",
            "reason": "Eligibility and funds verified."
        }, format="json")
        assert approve_res.status_code == status.HTTP_200_OK
        payout2.refresh_from_db()
        assert payout2.status == PayoutStatus.APPROVED

        # 6. Execute payout with reference and check ledger debit
        exec_res = self.client.post(f"/api/v1/payouts/{payout2.id}/execute/", {
            "execution_reference": "BANK-OUT-2026-001",
            "notes": "Direct transfer to Chala Bekele CBE Account"
        }, format="json")
        assert exec_res.status_code == status.HTTP_200_OK
        payout2.refresh_from_db()
        assert payout2.status == PayoutStatus.COMPLETED
        assert LedgerEntry.objects.filter(payout=payout2, direction=LedgerEntry.Direction.DEBIT).exists()
        assert get_group_available_funds(self.group) == Decimal("3000.00")
