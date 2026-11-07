import io
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership, GroupInvitation
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.contributions.models import ContributionPeriod, ContributionObligation
from apps.payments.models import (
    Payment, PaymentMethod, PaymentStatus, SettlementStatus,
    PaymentAllocation, GroupPaymentDestination
)
from apps.payouts.models import Payout, PayoutStatus
from apps.rules.models import RuleVersion, RuleApproval
from apps.disputes.models import Dispute, DisputeCategory, DisputeStatus
from apps.notifications.models import Notification
from apps.audit_app.models import Announcement


class TestMemberFullSuite(APITestCase):
    def setUp(self):
        ensure_permissions_seeded()

        self.org_role = GroupRole.objects.get(group=None, code="GROUP_ORGANIZER")
        self.treasurer_role = GroupRole.objects.get(group=None, code="GROUP_TREASURER")
        self.member_role = GroupRole.objects.get(group=None, code="GROUP_MEMBER")

        # 1. Organizer
        self.organizer = User.objects.create_user(
            email="org_selam@example.com",
            password="Password123!",
            full_name="Selam Organizer"
        )

        # 2. Treasurer
        self.treasurer = User.objects.create_user(
            email="tre_abebe@example.com",
            password="Password123!",
            full_name="Abebe Treasurer"
        )

        # 3. Member A (Primary test subject)
        self.member_a = User.objects.create_user(
            email="mem_dawit@example.com",
            password="Password123!",
            full_name="Dawit Member"
        )

        # 4. Member B (For isolation and IDOR checks)
        self.member_b = User.objects.create_user(
            email="mem_hana@example.com",
            password="Password123!",
            full_name="Hana Member"
        )

        # 5. Group 1: Unity Business Equb (Member A and B enrolled)
        self.group_1 = EqubGroup.objects.create(
            name="Unity Business Equb",
            organizer=self.organizer,
            status=EqubGroup.GroupStatus.ACTIVE,
            verification_status=EqubGroup.VerificationStatus.VERIFIED,
            currency="ETB",
            contribution_amount=Decimal("5000.00"),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=10,
            start_date=date(2025, 1, 1),
            group_purpose="Commercial business group"
        )

        # 6. Group 2: Family Support Equb (Only Member A enrolled)
        self.group_2 = EqubGroup.objects.create(
            name="Family Support Equb",
            organizer=self.organizer,
            status=EqubGroup.GroupStatus.ACTIVE,
            verification_status=EqubGroup.VerificationStatus.VERIFIED,
            currency="ETB",
            contribution_amount=Decimal("3000.00"),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=8,
            start_date=date(2025, 2, 1),
            group_purpose="Family savings"
        )

        # 7. Group 3: Private Closed Equb (Member A NOT enrolled)
        self.group_3 = EqubGroup.objects.create(
            name="Private Executive Equb",
            organizer=self.organizer,
            status=EqubGroup.GroupStatus.ACTIVE,
            verification_status=EqubGroup.VerificationStatus.VERIFIED,
            currency="ETB",
            contribution_amount=Decimal("10000.00"),
            capacity=5,
            start_date=date(2025, 3, 1)
        )

        # Assign Memberships
        self.m_a1 = GroupMembership.objects.create(
            group=self.group_1,
            user=self.member_a,
            status=GroupMembership.MembershipStatus.ACTIVE,
            payout_order_index=1,
            joined_at=timezone.now()
        )
        MembershipRoleAssignment.objects.create(membership=self.m_a1, role=self.member_role)

        self.m_a2 = GroupMembership.objects.create(
            group=self.group_2,
            user=self.member_a,
            status=GroupMembership.MembershipStatus.ACTIVE,
            payout_order_index=2,
            joined_at=timezone.now()
        )
        MembershipRoleAssignment.objects.create(membership=self.m_a2, role=self.member_role)

        self.m_b1 = GroupMembership.objects.create(
            group=self.group_1,
            user=self.member_b,
            status=GroupMembership.MembershipStatus.ACTIVE,
            payout_order_index=3,
            joined_at=timezone.now()
        )
        MembershipRoleAssignment.objects.create(membership=self.m_b1, role=self.member_role)

        # Create Contribution Periods
        self.p1_g1 = ContributionPeriod.objects.create(
            group=self.group_1, period_number=1,
            start_date=date(2025, 4, 1), due_date=date(2025, 4, 30), status=ContributionPeriod.PeriodStatus.SETTLED
        )
        self.p2_g1 = ContributionPeriod.objects.create(
            group=self.group_1, period_number=2,
            start_date=date(2025, 5, 1), due_date=date(2025, 5, 30), status=ContributionPeriod.PeriodStatus.OPEN
        )

        # Obligations for Member A
        self.ob1_a = ContributionObligation.objects.create(
            group=self.group_1, membership=self.m_a1, period=self.p1_g1,
            expected_amount=Decimal("5000.00"), amount_paid=Decimal("5000.00"),
            due_date=date(2025, 4, 30), status=ContributionObligation.ObligationStatus.PAID
        )
        self.ob2_a = ContributionObligation.objects.create(
            group=self.group_1, membership=self.m_a1, period=self.p2_g1,
            expected_amount=Decimal("5000.00"), amount_paid=Decimal("0.00"),
            due_date=date(2025, 5, 30), status=ContributionObligation.ObligationStatus.PENDING
        )

        # Payment for Member A (Paid obligation 1)
        self.pay_a = Payment.objects.create(
            receipt_number="TXN-M-001",
            group=self.group_1,
            obligation=self.ob1_a,
            payer=self.member_a,
            payment_method=PaymentMethod.BANK_TRANSFER,
            amount=Decimal("5000.00"),
            status=PaymentStatus.CONFIRMED,
            settlement_status=SettlementStatus.SETTLED,
            transfer_reference="CBE-M-001",
            verified_by=self.treasurer,
            verified_at=timezone.now()
        )

        # Payment for Member B (Private payment in Group 1)
        self.ob1_b = ContributionObligation.objects.create(
            group=self.group_1, membership=self.m_b1, period=self.p1_g1,
            expected_amount=Decimal("5000.00"), amount_paid=Decimal("5000.00"),
            due_date=date(2025, 4, 30), status=ContributionObligation.ObligationStatus.PAID
        )
        self.pay_b = Payment.objects.create(
            receipt_number="TXN-M-002-SECRET",
            group=self.group_1,
            obligation=self.ob1_b,
            payer=self.member_b,
            payment_method=PaymentMethod.DIGITAL_PROVIDER,
            amount=Decimal("5000.00"),
            status=PaymentStatus.CONFIRMED,
            settlement_status=SettlementStatus.SETTLED,
            provider_transaction_reference="TELE-SECRET-B"
        )

        # Rules for Group 1
        self.rule_v1 = RuleVersion.objects.create(
            group=self.group_1,
            version_number=1,
            title="Standard Rules",
            terms_text="Group agreement terms",
            contribution_amount=Decimal("5000.00"),
            status=RuleVersion.RuleStatus.APPROVED,
            proposed_by=self.organizer
        )
        self.group_1.active_rules_version = self.rule_v1
        self.group_1.save()

        self.rule_v2 = RuleVersion.objects.create(
            group=self.group_1,
            version_number=2,
            title="Proposed Terms Amendment",
            terms_text="Proposed amendment to monthly meeting time",
            contribution_amount=Decimal("5000.00"),
            status=RuleVersion.RuleStatus.PROPOSED,
            proposed_by=self.organizer
        )

    def test_unauthenticated_blocked(self):
        """Unauthenticated requests are blocked from all member endpoints."""
        endpoints = [
            "/api/v1/member/dashboard/",
            "/api/v1/member/groups/",
            "/api/v1/member/contributions/",
            "/api/v1/member/payments/",
            "/api/v1/member/payout-schedule/",
            "/api/v1/member/notifications/",
            "/api/v1/member/profile/"
        ]
        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED, f"Endpoint {ep} should require auth")

    def test_member_dashboard_kpis_and_groups(self):
        """Member retrieves dashboard overview with 5 accurate KPIs and group cards."""
        self.client.force_authenticate(user=self.member_a)
        res = self.client.get("/api/v1/member/dashboard/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data["member_name"], "Dawit Member")
        kpis = data["kpis"]
        self.assertEqual(kpis["joined_groups_count"], 2)
        self.assertEqual(Decimal(str(kpis["confirmed_contributions_etb"])), Decimal("5000.00"))
        self.assertEqual(Decimal(str(kpis["outstanding_contributions_etb"])), Decimal("5000.00"))
        self.assertEqual(len(data["my_groups"]), 2)
        self.assertEqual(len(data["upcoming_reminders"]), 3)
        self.assertEqual(len(data["recent_activity"]), 5)

    def test_group_details_and_sanitized_member_roster(self):
        """Member retrieves group detail and confirms other members' private info is hidden."""
        self.client.force_authenticate(user=self.member_a)
        res = self.client.get(f"/api/v1/member/groups/{self.group_1.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data["group"]["name"], "Unity Business Equb")
        self.assertEqual(len(data["sanitized_members"]), 2)

        # Verify Member B appears in roster with ONLY sanitized public info
        member_b_item = next(m for m in data["sanitized_members"] if m["name"] == "Hana Member")
        self.assertNotIn("phone_number", member_b_item)
        self.assertNotIn("email", member_b_item)
        self.assertFalse(member_b_item["is_you"])

        # Verify Member B's payment is NOT in Member A's group payments list
        my_payments = data["payments"]
        receipt_numbers = [p["receipt_number"] for p in my_payments]
        self.assertIn("TXN-M-001", receipt_numbers)
        self.assertNotIn("TXN-M-002-SECRET", receipt_numbers)

    def test_cross_group_authorization_isolation(self):
        """Member A cannot access group details for a group they have not joined."""
        self.client.force_authenticate(user=self.member_a)
        res = self.client.get(f"/api/v1/member/groups/{self.group_3.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_owned_contributions_and_payments_only(self):
        """Member A can only see their own contributions and payments (IDOR prevention)."""
        self.client.force_authenticate(user=self.member_a)

        # Contributions list
        res_obs = self.client.get("/api/v1/member/contributions/")
        self.assertEqual(res_obs.status_code, status.HTTP_200_OK)
        ob_ids = [o["id"] for o in res_obs.data]
        self.assertIn(str(self.ob1_a.id), ob_ids)
        self.assertIn(str(self.ob2_a.id), ob_ids)
        self.assertNotIn(str(self.ob1_b.id), ob_ids)

        # Payments list
        res_pay = self.client.get("/api/v1/member/payments/")
        self.assertEqual(res_pay.status_code, status.HTTP_200_OK)
        pay_receipts = [p["receipt_number"] for p in res_pay.data]
        self.assertIn("TXN-M-001", pay_receipts)
        self.assertNotIn("TXN-M-002-SECRET", pay_receipts)

    def test_digital_payment_initiation(self):
        """Member initiates digital Telebirr payment for an obligation."""
        self.client.force_authenticate(user=self.member_a)
        res = self.client.post(f"/api/v1/member/obligations/{self.ob2_a.id}/pay-digital/", {
            "provider_name": "TEST_TELEBIRR_ADAPTER"
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data.get("attempt_id") or res.data.get("internal_reference"))

    def test_bank_transfer_submission(self):
        """Member submits bank transfer reference. Status must be PENDING_VERIFICATION."""
        self.client.force_authenticate(user=self.member_a)
        res = self.client.post(f"/api/v1/member/obligations/{self.ob2_a.id}/submit-transfer/", {
            "obligation_id": str(self.ob2_a.id),
            "transfer_reference": "CBE-REF-998877",
            "amount": "5000.00",
            "notes": "Paid at branch"
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Verify payment in DB
        payment = Payment.objects.get(transfer_reference="CBE-REF-998877")
        self.assertEqual(payment.status, PaymentStatus.PENDING_VERIFICATION)
        self.assertEqual(payment.payer, self.member_a)

    def test_receipt_detail_access_and_unauthorized_receipt_blocked(self):
        """Member can access their own receipt slip, but cannot view another member's receipt."""
        self.client.force_authenticate(user=self.member_a)

        # Own receipt
        res_own = self.client.get(f"/api/v1/member/receipts/{self.pay_a.receipt_number}/")
        self.assertEqual(res_own.status_code, status.HTTP_200_OK)
        self.assertEqual(res_own.data["receipt_number"], "TXN-M-001")

        # Other member's receipt
        res_other = self.client.get(f"/api/v1/member/receipts/{self.pay_b.receipt_number}/")
        self.assertEqual(res_other.status_code, status.HTTP_404_NOT_FOUND)

    def test_invitation_acceptance_and_decline(self):
        """Member accepts a pending invitation and joins the group."""
        invitation = GroupInvitation.objects.create(
            group=self.group_3,
            invited_email=self.member_a.email,
            token="INVITE-TEST-TOKEN-123",
            status=GroupInvitation.InvitationStatus.PENDING,
            expires_at=timezone.now() + timedelta(days=7)
        )

        self.client.force_authenticate(user=self.member_a)
        res = self.client.post(f"/api/v1/member/invitations/{invitation.id}/action/", {
            "action": "accept"
        })
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data.get("success"))

        # Verify Member A is now an active member of Group 3
        membership = GroupMembership.objects.filter(group=self.group_3, user=self.member_a).first()
        self.assertIsNotNone(membership)
        self.assertEqual(membership.status, GroupMembership.MembershipStatus.ACTIVE)

    def test_membership_request_workflow(self):
        """Member requests to join an open group."""
        self.client.force_authenticate(user=self.member_b)
        res = self.client.post(f"/api/v1/member/groups/{self.group_2.id}/membership-requests/")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Verify status is REQUESTED
        membership = GroupMembership.objects.get(group=self.group_2, user=self.member_b)
        self.assertEqual(membership.status, GroupMembership.MembershipStatus.REQUESTED)

    def test_rule_version_view_and_voting(self):
        """Member views rule versions and casts an approval vote."""
        self.client.force_authenticate(user=self.member_a)

        # List rules
        res_rules = self.client.get(f"/api/v1/member/groups/{self.group_1.id}/rules/")
        self.assertEqual(res_rules.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_rules.data), 2)

        # Vote on proposed version 2
        res_vote = self.client.post(f"/api/v1/member/groups/{self.group_1.id}/rules/{self.rule_v2.id}/vote/", {
            "decision": "APPROVED",
            "comment": "I agree with meeting timing change"
        })
        self.assertEqual(res_vote.status_code, status.HTTP_200_OK)
        self.assertTrue(res_vote.data.get("success"))

        # Verify vote recorded in DB
        vote = RuleApproval.objects.get(rule_version=self.rule_v2, membership=self.m_a1)
        self.assertEqual(vote.decision, RuleApproval.Decision.APPROVED)

    def test_dispute_submission_and_reopen(self):
        """Member submits a dispute, reads it, and reopens it."""
        self.client.force_authenticate(user=self.member_a)

        # Submit dispute
        res = self.client.post("/api/v1/member/disputes/", {
            "group_id": str(self.group_1.id),
            "category": DisputeCategory.PAYMENT_NOT_RECORDED,
            "title": "Payment missing from statement",
            "description": "I deposited 5000 ETB on Monday."
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        dispute_id = res.data.get("dispute_id")

        # View detail
        res_detail = self.client.get(f"/api/v1/member/disputes/{dispute_id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["title"], "Payment missing from statement")

        # Reopen dispute
        res_reopen = self.client.post(f"/api/v1/member/disputes/{dispute_id}/reopen/", {
            "reason": "Still not showing up in my confirmed list."
        })
        self.assertEqual(res_reopen.status_code, status.HTTP_200_OK)
        dispute = Dispute.objects.get(id=dispute_id)
        self.assertEqual(dispute.status, DisputeStatus.REOPENED)

    def test_notifications_list_and_mark_read(self):
        """Member retrieves in-app notifications and marks them as read."""
        notif = Notification.objects.create(
            user=self.member_a,
            group=self.group_1,
            title="Payment Received",
            message="Your payment was credited",
            is_read=False
        )

        self.client.force_authenticate(user=self.member_a)
        res_list = self.client.get("/api/v1/member/notifications/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res_list.data), 1)

        # Mark read
        res_read = self.client.post(f"/api/v1/member/notifications/{notif.id}/read/")
        self.assertEqual(res_read.status_code, status.HTTP_200_OK)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_profile_update_and_password_change(self):
        """Member updates profile fields and changes password securely."""
        self.client.force_authenticate(user=self.member_a)

        # Update profile
        res_patch = self.client.patch("/api/v1/member/profile/", {
            "full_name": "Dawit A. Kebede",
            "phone_number": "+251 988 776 655",
            "preferred_language": "am"
        })
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.member_a.refresh_from_db()
        self.assertEqual(self.member_a.full_name, "Dawit A. Kebede")
        self.assertEqual(self.member_a.preferred_language, "am")

        # Change password
        res_pass = self.client.post("/api/v1/member/profile/", {
            "old_password": "Password123!",
            "new_password": "NewSecretPassword999!"
        })
        self.assertEqual(res_pass.status_code, status.HTTP_200_OK)
        self.member_a.refresh_from_db()
        self.assertTrue(self.member_a.check_password("NewSecretPassword999!"))
