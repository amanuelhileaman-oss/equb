import io
import csv
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.contributions.models import ContributionPeriod, ContributionObligation
from apps.payments.models import (
    Payment, PaymentMethod, PaymentStatus, SettlementStatus,
    ReconciliationException
)
from apps.payouts.models import Payout, PayoutStatus, PayoutSettlementStatus
from apps.ledger.models import LedgerEntry
from apps.ledger.services import record_contribution_ledger


class TestTreasurerFullSuite(APITestCase):
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

        # 3. Regular Member
        self.member = User.objects.create_user(
            email="mem_dawit@example.com",
            password="Password123!",
            full_name="Dawit Member"
        )

        # 4. Another user for cross-group test
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="Password123!",
            full_name="Other User"
        )

        # Group A: Where Abebe is Treasurer
        self.group_a = EqubGroup.objects.create(
            name="Unity Business Equb",
            organizer=self.organizer,
            contribution_amount=Decimal("5000.00"),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            status=EqubGroup.GroupStatus.ACTIVE,
            verification_status=EqubGroup.VerificationStatus.VERIFIED,
            start_date=date(2025, 1, 1),
            require_cash_second_confirmation=True
        )

        # Group B: Where Abebe is NOT Treasurer (only a regular member)
        self.group_b = EqubGroup.objects.create(
            name="Merkato Merchants Equb",
            organizer=self.organizer,
            contribution_amount=Decimal("10000.00"),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            status=EqubGroup.GroupStatus.ACTIVE,
            verification_status=EqubGroup.VerificationStatus.VERIFIED,
            start_date=date(2025, 1, 1),
            require_cash_second_confirmation=False
        )

        # Memberships for Group A
        self.m_org_a = GroupMembership.objects.create(
            group=self.group_a, user=self.organizer, status=GroupMembership.MembershipStatus.ACTIVE, payout_order_index=1
        )
        MembershipRoleAssignment.objects.create(membership=self.m_org_a, role=self.org_role)

        self.m_tre_a = GroupMembership.objects.create(
            group=self.group_a, user=self.treasurer, status=GroupMembership.MembershipStatus.ACTIVE, payout_order_index=2
        )
        self.tre_assignment_a = MembershipRoleAssignment.objects.create(membership=self.m_tre_a, role=self.treasurer_role)

        self.m_mem_a = GroupMembership.objects.create(
            group=self.group_a, user=self.member, status=GroupMembership.MembershipStatus.ACTIVE, payout_order_index=3
        )
        MembershipRoleAssignment.objects.create(membership=self.m_mem_a, role=self.member_role)

        # Memberships for Group B (Treasurer is ONLY regular member here!)
        self.m_org_b = GroupMembership.objects.create(
            group=self.group_b, user=self.organizer, status=GroupMembership.MembershipStatus.ACTIVE, payout_order_index=1
        )
        MembershipRoleAssignment.objects.create(membership=self.m_org_b, role=self.org_role)

        self.m_tre_b = GroupMembership.objects.create(
            group=self.group_b, user=self.treasurer, status=GroupMembership.MembershipStatus.ACTIVE, payout_order_index=2
        )
        MembershipRoleAssignment.objects.create(membership=self.m_tre_b, role=self.member_role) # Member role ONLY!

        # Period for Group A
        self.period_a = ContributionPeriod.objects.create(
            group=self.group_a,
            period_number=1,
            start_date=date(2025, 6, 1),
            due_date=date(2025, 6, 30),
            status=ContributionPeriod.PeriodStatus.OPEN
        )

        # Obligation for Dawit in Group A
        self.obligation_a = ContributionObligation.objects.create(
            group=self.group_a,
            membership=self.m_mem_a,
            period=self.period_a,
            expected_amount=Decimal("5000.00"),
            amount_paid=Decimal("0.00"),
            currency="ETB",
            due_date=date(2025, 6, 30),
            status=ContributionObligation.ObligationStatus.PENDING
        )

    def test_unauthenticated_and_regular_member_blocked(self):
        """Unauthenticated requests or requests from regular members are rejected."""
        # Unauthenticated
        res = self.client.get('/api/v1/treasurer/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Regular member
        self.client.force_authenticate(user=self.member)
        res = self.client.get(f'/api/v1/treasurer/groups/{self.group_a.id}/contributions/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_treasurer_dashboard_retrieval(self):
        """Authenticated Treasurer retrieves aggregated KPIs, chart points, and groups."""
        self.client.force_authenticate(user=self.treasurer)
        res = self.client.get('/api/v1/treasurer/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['treasurer_name'], "Abebe Treasurer")
        self.assertIn('kpis', res.data)
        self.assertIn('financial_overview_chart', res.data)
        self.assertIn('your_groups', res.data)
        self.assertIn('recent_transactions', res.data)

    def test_cross_group_authorization_isolation(self):
        """
        Treasurer in Group A cannot perform treasurer actions in Group B
        where they only have regular Member status.
        """
        self.client.force_authenticate(user=self.treasurer)

        # Can access Group A
        res_a = self.client.get(f'/api/v1/treasurer/groups/{self.group_a.id}/')
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)

        # Blocked from Group B
        res_b = self.client.get(f'/api/v1/treasurer/groups/{self.group_b.id}/')
        self.assertEqual(res_b.status_code, status.HTTP_403_FORBIDDEN)

    def test_cash_receipt_recording_and_validation(self):
        """Treasurer records cash receipt with valid amount and obligation."""
        self.client.force_authenticate(user=self.treasurer)

        # Amount exceeding obligation rejected
        bad_res = self.client.post(
            f'/api/v1/treasurer/groups/{self.group_a.id}/cash-receipts/',
            {'obligation_id': str(self.obligation_a.id), 'amount': '6000.00'}
        )
        self.assertEqual(bad_res.status_code, status.HTTP_400_BAD_REQUEST)

        # Valid recording
        good_res = self.client.post(
            f'/api/v1/treasurer/groups/{self.group_a.id}/cash-receipts/',
            {
                'obligation_id': str(self.obligation_a.id),
                'amount': '5000.00',
                'receipt_number': 'RCP-TEST-001',
                'notes': 'Paid in person'
            }
        )
        self.assertEqual(good_res.status_code, status.HTTP_201_CREATED)
        # Because Group A requires 2nd confirmation, status is PENDING_VERIFICATION
        self.assertEqual(good_res.data['status'], PaymentStatus.PENDING_VERIFICATION)

    def test_duplicate_cash_receipt_number_rejected(self):
        """Duplicate receipt numbers are strictly rejected."""
        self.client.force_authenticate(user=self.treasurer)

        self.client.post(
            f'/api/v1/treasurer/groups/{self.group_a.id}/cash-receipts/',
            {'obligation_id': str(self.obligation_a.id), 'amount': '2000.00', 'receipt_number': 'RCP-DUP-1'}
        )

        res = self.client.post(
            f'/api/v1/treasurer/groups/{self.group_a.id}/cash-receipts/',
            {'obligation_id': str(self.obligation_a.id), 'amount': '1000.00', 'receipt_number': 'RCP-DUP-1'}
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already recorded', str(res.data))

    def test_cash_receipt_second_person_verification_and_separation_of_duties(self):
        """
        When dual-check is required, the Treasurer who received cash CANNOT self-approve it.
        Another authorized user (Organizer) can independently confirm it.
        """
        # Treasurer records cash
        self.client.force_authenticate(user=self.treasurer)
        create_res = self.client.post(
            f'/api/v1/treasurer/groups/{self.group_a.id}/cash-receipts/',
            {'obligation_id': str(self.obligation_a.id), 'amount': '5000.00', 'receipt_number': 'RCP-DUAL-01'}
        )
        payment_id = create_res.data['id']

        # Treasurer attempts to verify their own cash entry -> BLOCKED (Separation of duties)
        self.client.force_authenticate(user=self.treasurer)
        self_approve_res = self.client.post(
            f'/api/v1/treasurer/approvals/cash/{payment_id}/action/',
            {'decision': 'APPROVE', 'reason': 'I approve myself'}
        )
        self.assertEqual(self_approve_res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Separation of duties', str(self_approve_res.data))

        # Organizer (different authorized user) confirms the cash receipt
        self.client.force_authenticate(user=self.organizer)
        approve_res = self.client.post(
            f'/api/v1/treasurer/approvals/cash/{payment_id}/action/',
            {'decision': 'APPROVE', 'reason': 'Physically counted cash in vault'}
        )
        self.assertEqual(approve_res.status_code, status.HTTP_200_OK)

        # Obligation is now fully paid and credited in ledger
        self.obligation_a.refresh_from_db()
        self.assertEqual(self.obligation_a.status, ContributionObligation.ObligationStatus.PAID)
        self.assertEqual(self.obligation_a.amount_paid, Decimal('5000.00'))

        # Ledger entry posted
        self.assertTrue(
            LedgerEntry.objects.filter(
                group=self.group_a,
                entry_type=LedgerEntry.EntryType.CONTRIBUTION_RECEIVED,
                amount=Decimal('5000.00')
            ).exists()
        )

    def test_bank_transfer_reconciliation_and_duplicate_prevention(self):
        """Treasurer reconciles member-submitted bank transfer against bank deposits."""
        # Member submits transfer
        payment = Payment.objects.create(
            receipt_number="RCP-TRF-001",
            group=self.group_a,
            obligation=self.obligation_a,
            payer=self.member,
            payment_method=PaymentMethod.BANK_TRANSFER,
            amount=Decimal("5000.00"),
            currency="ETB",
            status=PaymentStatus.PENDING_VERIFICATION,
            transfer_reference="TXN-BANK-8899"
        )

        self.client.force_authenticate(user=self.treasurer)

        # Confirm transfer
        res = self.client.post(
            f'/api/v1/treasurer/groups/{self.group_a.id}/reconciliation/match/',
            {'payment_id': str(payment.id), 'decision': 'CONFIRM', 'notes': 'Verified on CBE statement'}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'CONFIRMED')

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.CONFIRMED)
        self.assertEqual(payment.settlement_status, SettlementStatus.SETTLED)

    def test_reconciliation_exception_flagging(self):
        """Treasurer flags reconciliation discrepancy."""
        self.client.force_authenticate(user=self.treasurer)

        res = self.client.post(
            f'/api/v1/treasurer/groups/{self.group_a.id}/reconciliation/exceptions/',
            {
                'exception_type': 'AMOUNT_MISMATCH',
                'reference_number': 'TXN-MISMATCH-123',
                'expected_amount': '5000.00',
                'actual_amount': '4500.00',
                'description': 'Member deposited 4,500 ETB instead of 5,000 ETB'
            }
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ReconciliationException.objects.filter(reference_number='TXN-MISMATCH-123').exists())

    def test_payout_preparation_and_insufficient_funds_blocked(self):
        """Payout requested with insufficient group funds is blocked."""
        self.client.force_authenticate(user=self.treasurer)

        # Currently 0 ETB in verified group ledger, requesting 50,000 ETB
        res = self.client.post(
            f'/api/v1/treasurer/groups/{self.group_a.id}/payouts/requests/',
            {'membership_id': str(self.m_mem_a.id), 'amount': '50000.00', 'notes': 'Round 1 payout'}
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['status'], PayoutStatus.BLOCKED_INSUFFICIENT_FUNDS)

    def test_payout_approval_separation_of_duties(self):
        """Requester of payout cannot approve it."""
        payout = Payout.objects.create(
            group=self.group_a,
            recipient_membership=self.m_mem_a,
            amount=Decimal("5000.00"),
            currency="ETB",
            requesting_user=self.treasurer,
            status=PayoutStatus.PENDING_APPROVAL
        )

        # Treasurer tries to approve own payout -> BLOCKED
        self.client.force_authenticate(user=self.treasurer)
        res = self.client.post(
            f'/api/v1/treasurer/approvals/payout/{payout.id}/action/',
            {'decision': 'APPROVE', 'reason': 'I approve'}
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Separation of duties', str(res.data))

        # Organizer approves -> ALLOWED
        self.client.force_authenticate(user=self.organizer)
        good_res = self.client.post(
            f'/api/v1/treasurer/approvals/payout/{payout.id}/action/',
            {'decision': 'APPROVE', 'reason': 'Approved by organizer'}
        )
        self.assertEqual(good_res.status_code, status.HTTP_200_OK)
        payout.refresh_from_db()
        self.assertEqual(payout.status, PayoutStatus.APPROVED)

    def test_payout_execution_and_ledger_debit(self):
        """Executing an approved payout posts a DEBIT entry to the ledger."""
        # Seed 10,000 ETB into treasury first
        pm = Payment.objects.create(
            receipt_number="RCP-FUNDS-01",
            group=self.group_a,
            payer=self.organizer,
            payment_method=PaymentMethod.DIGITAL_PROVIDER,
            amount=Decimal("10000.00"),
            currency="ETB",
            status=PaymentStatus.CONFIRMED,
            settlement_status=SettlementStatus.SETTLED,
            verified_at=timezone.now()
        )
        record_contribution_ledger(pm, posted_by=self.treasurer)

        payout = Payout.objects.create(
            group=self.group_a,
            recipient_membership=self.m_mem_a,
            amount=Decimal("5000.00"),
            currency="ETB",
            requesting_user=self.organizer,
            status=PayoutStatus.APPROVED
        )

        self.client.force_authenticate(user=self.treasurer)
        res = self.client.post(
            f'/api/v1/treasurer/payouts/{payout.id}/execution-evidence/',
            {'execution_reference': 'CBE-TX-44882', 'notes': 'Transferred to Dawit commercial bank account'}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], PayoutStatus.COMPLETED)

        # Check DEBIT posted
        self.assertTrue(
            LedgerEntry.objects.filter(
                group=self.group_a,
                entry_type=LedgerEntry.EntryType.PAYOUT_DISBURSED,
                direction=LedgerEntry.Direction.DEBIT,
                amount=Decimal('5000.00')
            ).exists()
        )

    def test_financial_reports_and_csv_formula_injection_prevention(self):
        """Reports CSV export sanitizes potential formula injection."""
        # Create member with dangerous formula name
        malicious_user = User.objects.create_user(
            email="hack@example.com",
            password="Password123!",
            full_name="=cmd|' /C calc'!A0"
        )
        m_mal = GroupMembership.objects.create(
            group=self.group_a, user=malicious_user, status=GroupMembership.MembershipStatus.ACTIVE, payout_order_index=10
        )
        ContributionObligation.objects.create(
            group=self.group_a,
            membership=m_mal,
            period=self.period_a,
            expected_amount=Decimal("5000.00"),
            currency="ETB",
            due_date=date(2025, 6, 30),
            status=ContributionObligation.ObligationStatus.PENDING
        )

        self.client.force_authenticate(user=self.treasurer)
        res = self.client.get(f'/api/v1/treasurer/groups/{self.group_a.id}/reports/export/?type=contributions')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'text/csv')

        csv_content = res.content.decode('utf-8')
        # Check formula is escaped with single quote
        self.assertIn("'=cmd|' /C calc'!A0", csv_content)

    def test_revoked_treasurer_permissions_immediately_stop_access(self):
        """Revoking the Treasurer role immediately revokes API access."""
        self.client.force_authenticate(user=self.treasurer)

        # Currently has access
        res = self.client.get(f'/api/v1/treasurer/groups/{self.group_a.id}/contributions/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Revoke role assignment
        self.tre_assignment_a.delete()

        # Immediately blocked
        res_after = self.client.get(f'/api/v1/treasurer/groups/{self.group_a.id}/contributions/')
        self.assertEqual(res_after.status_code, status.HTTP_403_FORBIDDEN)
