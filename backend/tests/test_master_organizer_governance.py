import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User, OrganizerProfile
from apps.groups.models import EqubGroup, GroupMembership, TreasurerAssignmentRecord
from apps.subscriptions.models import SaasPlan, OrganizerSubscription, SubscriptionInvoice
from apps.audit_app.models import SecurityIncident, SecurityEvent, AuditLog, Announcement
from apps.notifications.models import Notification
from apps.contributions.models import ContributionObligation, ContributionPeriod
from apps.payouts.models import Payout, PayoutStatus, PayoutApproval


class TestMasterOrganizerGovernanceSuite(APITestCase):
    """
    Comprehensive verification suite for Master Organizer Governance:
    - Super Admin Organizer Onboarding & Nigd Fikad Verification
    - Subscription Payment Gate & Dashboard Unlock
    - Group Creation with/without Organizer Self-Membership
    - Member Creation, Capacity Enforcement & Bulk CSV Import
    - Treasurer Assignment with Audit History
    - Automated Financial Security Monitor & Incident Response
    """

    def setUp(self):
        # 1. Super Admin
        self.superadmin = User.objects.create_user(
            email="superadmin.gov@digitalequb.et",
            password="AdminPass123!",
            full_name="Super Admin Governor",
            is_platform_admin=True,
            is_staff=True,
            is_superuser=True,
            account_status=User.AccountStatus.ACTIVE
        )

        # 2. SaaS Plans
        self.starter_plan = SaasPlan.objects.create(
            code="STARTER",
            name="Starter Plan",
            price_etb=Decimal('500.00'),
            max_active_groups=3,
            is_active=True
        )
        self.growth_plan = SaasPlan.objects.create(
            code="GROWTH",
            name="Growth Business Plan",
            price_etb=Decimal('1500.00'),
            max_active_groups=10,
            is_active=True
        )

    def test_01_superadmin_creates_organizer_account(self):
        """Super Admin creates an Organizer account with business and Nigd Fikad license details."""
        self.client.force_authenticate(user=self.superadmin)
        payload = {
            "full_legal_name": "Ato Dawit Kebede",
            "email": "dawit.organizer@example.com",
            "phone_number": "+251911998877",
            "business_name": "Kebede Trading PLC",
            "business_type": "PLC",
            "business_address": "Bole Subcity, Woreda 03, House 450, Addis Ababa",
            "license_number": "NF-AA-2026-98765",
            "license_document": "data:application/pdf;base64,JVBERi0xLjQK...",
            "assigned_plan_id": str(self.growth_plan.id),
            "subscription_amount": "1500.00",
            "billing_period": "MONTHLY",
            "verification_notes": "Valid Addis Ababa Trade Bureau Nigd Fikad verified."
        }
        response = self.client.post("/api/v1/admin/organizers/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data.get("success"))

        org_user = User.objects.get(email="dawit.organizer@example.com")
        self.assertEqual(org_user.full_name, "Ato Dawit Kebede")
        self.assertTrue(hasattr(org_user, "organizer_profile"))
        profile = org_user.organizer_profile
        self.assertEqual(profile.business_name, "Kebede Trading PLC")
        self.assertEqual(profile.license_number, "NF-AA-2026-98765")
        self.assertEqual(profile.verification_status, OrganizerProfile.VerificationStatus.PENDING_VERIFICATION)
        self.assertEqual(profile.payment_status, OrganizerProfile.PaymentStatus.PAYMENT_REQUIRED)

    def test_02_unapproved_organizer_blocked_at_dashboard_gate(self):
        """Unapproved organizer receives gate_blocked=True and is prevented from managing groups."""
        org_user = User.objects.create_user(
            email="pending.org@example.com",
            password="SecurePass123!",
            full_name="Pending Organizer",
            account_status=User.AccountStatus.ACTIVE
        )
        OrganizerProfile.objects.create(
            user=org_user,
            business_name="Pending Enterprise",
            verification_status=OrganizerProfile.VerificationStatus.PENDING_VERIFICATION,
            payment_status=OrganizerProfile.PaymentStatus.PAYMENT_REQUIRED,
            assigned_plan=self.starter_plan
        )

        self.client.force_authenticate(user=org_user)
        # Dashboard shows gate blocked
        dash_res = self.client.get("/api/v1/organizer/dashboard/")
        self.assertEqual(dash_res.status_code, status.HTTP_200_OK)
        self.assertTrue(dash_res.data.get("gate_blocked"))
        self.assertEqual(dash_res.data.get("gate_reason"), "VERIFICATION_PENDING")

        # Creating a group is forbidden by gate
        group_res = self.client.post("/api/v1/organizer/groups/", {
            "name": "Unauthorized Group",
            "contribution_amount": "1000.00",
            "contribution_frequency": "MONTHLY",
            "max_members": 12
        }, format="json")
        self.assertEqual(group_res.status_code, status.HTTP_403_FORBIDDEN)

    def test_03_approved_unpaid_organizer_blocked_at_payment_gate(self):
        """Approved organizer with pending subscription payment is blocked until payment confirmation."""
        org_user = User.objects.create_user(
            email="approved.unpaid@example.com",
            password="SecurePass123!",
            full_name="Approved But Unpaid",
            account_status=User.AccountStatus.ACTIVE
        )
        OrganizerProfile.objects.create(
            user=org_user,
            business_name="Approved Ventures",
            verification_status=OrganizerProfile.VerificationStatus.APPROVED,
            payment_status=OrganizerProfile.PaymentStatus.PAYMENT_REQUIRED,
            assigned_plan=self.starter_plan
        )

        self.client.force_authenticate(user=org_user)
        dash_res = self.client.get("/api/v1/organizer/dashboard/")
        self.assertEqual(dash_res.status_code, status.HTTP_200_OK)
        self.assertTrue(dash_res.data.get("gate_blocked"))
        self.assertEqual(dash_res.data.get("gate_reason"), "PAYMENT_REQUIRED")

        # Group creation forbidden
        group_res = self.client.post("/api/v1/organizer/groups/", {
            "name": "Unpaid Group",
            "contribution_amount": "2000.00",
            "contribution_frequency": "MONTHLY",
            "max_members": 10
        }, format="json")
        self.assertEqual(group_res.status_code, status.HTTP_403_FORBIDDEN)

    def test_04_subscription_payment_unlocks_organizer_dashboard(self):
        """Organizer pays subscription fee; gate is immediately unlocked and dashboard accessible."""
        org_user = User.objects.create_user(
            email="payer.org@example.com",
            password="SecurePass123!",
            full_name="Payer Organizer",
            account_status=User.AccountStatus.ACTIVE
        )
        prof = OrganizerProfile.objects.create(
            user=org_user,
            business_name="Payer Enterprise",
            verification_status=OrganizerProfile.VerificationStatus.APPROVED,
            payment_status=OrganizerProfile.PaymentStatus.PAYMENT_REQUIRED,
            assigned_plan=self.starter_plan,
            subscription_amount=Decimal('500.00')
        )

        self.client.force_authenticate(user=org_user)
        # Pay subscription
        pay_res = self.client.post("/api/v1/organizer/subscription/pay/", {
            "provider": "TELEBIRR",
            "payment_reference": "TLB-REC-2026-7788"
        }, format="json")
        self.assertEqual(pay_res.status_code, status.HTTP_200_OK)
        self.assertTrue(pay_res.data.get("success"))
        self.assertTrue(pay_res.data.get("gate_unlocked"))

        prof.refresh_from_db()
        self.assertEqual(prof.payment_status, OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED)
        self.assertTrue(prof.is_dashboard_accessible)

        # Dashboard now returns gate_blocked=False
        dash_res = self.client.get("/api/v1/organizer/dashboard/")
        self.assertEqual(dash_res.status_code, status.HTTP_200_OK)
        self.assertFalse(dash_res.data.get("gate_blocked"))

    def test_05_group_creation_without_self_membership(self):
        """Organizer creates a group without participating as a member (default behavior)."""
        org_user = User.objects.create_user(
            email="active.org1@example.com",
            password="SecurePass123!",
            full_name="Active Organizer 1",
            account_status=User.AccountStatus.ACTIVE
        )
        OrganizerProfile.objects.create(
            user=org_user,
            business_name="Active Org 1 PLC",
            verification_status=OrganizerProfile.VerificationStatus.APPROVED,
            payment_status=OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED,
            assigned_plan=self.growth_plan
        )
        OrganizerSubscription.objects.create(
            organizer=org_user,
            plan=self.growth_plan,
            status=OrganizerSubscription.SubscriptionStatus.ACTIVE,
            started_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30)
        )

        self.client.force_authenticate(user=org_user)
        res = self.client.post("/api/v1/organizer/groups/", {
            "name": "Bole Business Equb",
            "contribution_amount": "5000.00",
            "contribution_frequency": "MONTHLY",
            "max_members": 20,
            "participate_as_member": False
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        group_id = res.data.get("id")

        group = EqubGroup.objects.get(id=group_id)
        membership = GroupMembership.objects.get(group=group, user=org_user)
        # Check roles: organizer role only, NOT group member
        role_codes = list(membership.role_assignments.values_list('role__code', flat=True))
        self.assertIn("GROUP_ORGANIZER", role_codes)
        self.assertNotIn("GROUP_MEMBER", role_codes)

        # No contribution obligations for organizer
        obligations_count = ContributionObligation.objects.filter(group=group, membership=membership).count()
        self.assertEqual(obligations_count, 0)

    def test_06_group_creation_with_self_membership(self):
        """Organizer creates a group and opts in to participate as a rotating member."""
        org_user = User.objects.create_user(
            email="active.org2@example.com",
            password="SecurePass123!",
            full_name="Active Organizer 2",
            account_status=User.AccountStatus.ACTIVE
        )
        OrganizerProfile.objects.create(
            user=org_user,
            business_name="Active Org 2 PLC",
            verification_status=OrganizerProfile.VerificationStatus.APPROVED,
            payment_status=OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED,
            assigned_plan=self.growth_plan
        )
        OrganizerSubscription.objects.create(
            organizer=org_user,
            plan=self.growth_plan,
            status=OrganizerSubscription.SubscriptionStatus.ACTIVE,
            started_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30)
        )

        self.client.force_authenticate(user=org_user)
        res = self.client.post("/api/v1/organizer/groups/", {
            "name": "Family Rotating Equb",
            "contribution_amount": "3000.00",
            "contribution_frequency": "MONTHLY",
            "max_members": 15,
            "participate_as_member": True
        }, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        group_id = res.data.get("id")

        group = EqubGroup.objects.get(id=group_id)
        membership = GroupMembership.objects.get(group=group, user=org_user)
        role_codes = list(membership.role_assignments.values_list('role__code', flat=True))
        self.assertIn("GROUP_ORGANIZER", role_codes)
        self.assertIn("GROUP_MEMBER", role_codes)

        # Obligation created for organizer
        obligations_count = ContributionObligation.objects.filter(group=group, membership=membership).count()
        self.assertEqual(obligations_count, 1)

    def test_07_member_creation_and_capacity_limits(self):
        """Organizer creates members and system strictly enforces max_members capacity."""
        org_user = User.objects.create_user(
            email="capacity.org@example.com",
            password="SecurePass123!",
            full_name="Capacity Tester",
            account_status=User.AccountStatus.ACTIVE
        )
        OrganizerProfile.objects.create(
            user=org_user,
            business_name="Capacity PLC",
            verification_status=OrganizerProfile.VerificationStatus.APPROVED,
            payment_status=OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED,
            assigned_plan=self.starter_plan
        )
        OrganizerSubscription.objects.create(
            organizer=org_user,
            plan=self.starter_plan,
            status=OrganizerSubscription.SubscriptionStatus.ACTIVE,
            started_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30)
        )
        group = EqubGroup.objects.create(
            organizer=org_user,
            name="Small Equb",
            contribution_amount=Decimal('1000.00'),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=2,
            start_date=date.today(),
            status=EqubGroup.GroupStatus.ACTIVE
        )
        # Period 1
        ContributionPeriod.objects.create(
            group=group,
            period_number=1,
            start_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=ContributionPeriod.PeriodStatus.OPEN
        )

        self.client.force_authenticate(user=org_user)
        # 1. Add Member 1
        res1 = self.client.post(f"/api/v1/organizer/groups/{group.id}/members/", {
            "full_name": "Tigist Haile",
            "email": "tigist.member@example.com",
            "phone_number": "+251922110011",
            "password_setup_method": "TEMPORARY_PASSWORD"
        }, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # 2. Add Member 2
        res2 = self.client.post(f"/api/v1/organizer/groups/{group.id}/members/", {
            "full_name": "Yonas Bekele",
            "email": "yonas.member@example.com",
            "phone_number": "+251922110022",
            "password_setup_method": "INVITATION_LINK"
        }, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        # 3. Add Member 3 (exceeds capacity max_members=2) -> Must be rejected
        res3 = self.client.post(f"/api/v1/organizer/groups/{group.id}/members/", {
            "full_name": "Solomon Girma",
            "email": "solomon.member@example.com",
            "phone_number": "+251922110033",
            "password_setup_method": "TEMPORARY_PASSWORD"
        }, format="json")
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("capacity", str(res3.data).lower())

    def test_08_bulk_member_csv_import(self):
        """Organizer imports multiple members in bulk with validation and duplicate prevention."""
        org_user = User.objects.create_user(
            email="bulk.org@example.com",
            password="SecurePass123!",
            full_name="Bulk Org",
            account_status=User.AccountStatus.ACTIVE
        )
        OrganizerProfile.objects.create(
            user=org_user,
            business_name="Bulk Org PLC",
            verification_status=OrganizerProfile.VerificationStatus.APPROVED,
            payment_status=OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED,
            assigned_plan=self.growth_plan
        )
        OrganizerSubscription.objects.create(
            organizer=org_user,
            plan=self.growth_plan,
            status=OrganizerSubscription.SubscriptionStatus.ACTIVE,
            started_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30)
        )
        group = EqubGroup.objects.create(
            organizer=org_user,
            name="Bulk Target Equb",
            contribution_amount=Decimal('2000.00'),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=50,
            start_date=date.today(),
            status=EqubGroup.GroupStatus.ACTIVE
        )
        ContributionPeriod.objects.create(
            group=group,
            period_number=1,
            start_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=ContributionPeriod.PeriodStatus.OPEN
        )

        self.client.force_authenticate(user=org_user)
        members_list = [
            {"full_name": "Abebe Bulk 1", "email": "bulk1@example.com", "phone_number": "+251933001101"},
            {"full_name": "Abebe Bulk 2", "email": "bulk2@example.com", "phone_number": "+251933001102"},
            {"full_name": "Abebe Bulk 3", "email": "bulk3@example.com", "phone_number": "+251933001103"},
        ]
        res = self.client.post(
            f"/api/v1/organizer/groups/{group.id}/members/import/",
            {"members": members_list, "password_setup_method": "INVITATION_LINK"},
            format="json"
        )
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertEqual(res.data.get("imported_count"), 3)
        self.assertEqual(group.memberships.count(), 3)

    def test_09_treasurer_assignment_and_revocation_history(self):
        """Organizer assigns eligible group member as Treasurer; tracks full history in TreasurerAssignmentRecord."""
        org_user = User.objects.create_user(
            email="treasurer.org@example.com",
            password="SecurePass123!",
            full_name="Treasurer Org",
            account_status=User.AccountStatus.ACTIVE
        )
        OrganizerProfile.objects.create(
            user=org_user,
            business_name="Treasurer Org PLC",
            verification_status=OrganizerProfile.VerificationStatus.APPROVED,
            payment_status=OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED,
            assigned_plan=self.growth_plan
        )
        OrganizerSubscription.objects.create(
            organizer=org_user,
            plan=self.growth_plan,
            status=OrganizerSubscription.SubscriptionStatus.ACTIVE,
            started_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=30)
        )
        group = EqubGroup.objects.create(
            organizer=org_user,
            name="Treasury Protected Equb",
            contribution_amount=Decimal('1500.00'),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=20,
            start_date=date.today(),
            status=EqubGroup.GroupStatus.ACTIVE
        )

        member_user = User.objects.create_user(
            email="candidate.treasurer@example.com",
            password="SecurePass123!",
            full_name="Candidate Treasurer",
            account_status=User.AccountStatus.ACTIVE
        )
        membership = GroupMembership.objects.create(
            group=group,
            user=member_user,
            status=GroupMembership.MembershipStatus.ACTIVE
        )

        self.client.force_authenticate(user=org_user)
        # Assign as Treasurer
        assign_res = self.client.post(f"/api/v1/organizer/groups/{group.id}/treasurer/", {
            "user_id": str(member_user.id),
            "notes": "Appointed chief treasurer for Bole Equb 2026."
        }, format="json")
        self.assertEqual(assign_res.status_code, status.HTTP_200_OK)
        self.assertTrue(assign_res.data.get("success"))

        # Verify active assignment record
        record = TreasurerAssignmentRecord.objects.get(group=group, user=member_user, is_active=True)
        self.assertEqual(record.assigned_by, org_user)
        self.assertIsNone(record.revoked_at)

        # Non-member cannot be assigned as treasurer
        stranger_user = User.objects.create_user(
            email="stranger@example.com",
            password="SecurePass123!",
            full_name="Stranger"
        )
        invalid_res = self.client.post(f"/api/v1/organizer/groups/{group.id}/treasurer/", {
            "user_id": str(stranger_user.id)
        }, format="json")
        self.assertEqual(invalid_res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_10_financial_security_monitor_blocks_unauthorized_action_and_creates_incident(self):
        """
        Security Monitor automatically blocks unauthorized financial actions,
        creates immutable SecurityIncident and SecurityEvent, and Super Admin can broadcast security notice.
        """
        org_user = User.objects.create_user(
            email="sec.org@example.com",
            password="SecurePass123!",
            full_name="Security Org",
            account_status=User.AccountStatus.ACTIVE
        )
        group = EqubGroup.objects.create(
            organizer=org_user,
            name="Security Audit Equb",
            contribution_amount=Decimal('5000.00'),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=15,
            start_date=date.today(),
            status=EqubGroup.GroupStatus.ACTIVE
        )
        attacker = User.objects.create_user(
            email="rogue.actor@example.com",
            password="SecurePass123!",
            full_name="Rogue Member",
            account_status=User.AccountStatus.ACTIVE
        )
        membership = GroupMembership.objects.create(
            group=group,
            user=attacker,
            status=GroupMembership.MembershipStatus.ACTIVE
        )

        # Attacker tries to record cash receipts without being Treasurer
        self.client.force_authenticate(user=attacker)
        initial_incident_count = SecurityIncident.objects.count()

        hack_res = self.client.post(f"/api/v1/treasurer/groups/{group.id}/cash-receipts/", {
            "membership_id": str(membership.id),
            "amount": "5000.00",
            "receipt_number": "FAKE-REC-999"
        }, format="json")
        # Must be blocked by PermissionDenied
        self.assertEqual(hack_res.status_code, status.HTTP_403_FORBIDDEN)

        # Verify that SecurityIncident was created
        self.assertEqual(SecurityIncident.objects.count(), initial_incident_count + 1)
        incident = SecurityIncident.objects.latest('timestamp')
        self.assertEqual(incident.user, attacker)
        self.assertEqual(incident.group, group)
        self.assertEqual(incident.status, SecurityIncident.IncidentStatus.BLOCKED)

        # Super Admin investigates incident and broadcasts security notice
        self.client.force_authenticate(user=self.superadmin)
        notify_res = self.client.post(
            f"/api/v1/admin/security-incidents/{incident.id}/notify-group/",
            {
                "title": "Platform Security Advisory",
                "content": "An unauthorized financial attempt was detected and blocked by our security monitor."
            },
            format="json"
        )
        self.assertEqual(notify_res.status_code, status.HTTP_200_OK)
        res_data = notify_res.data if hasattr(notify_res, 'data') else notify_res.json()
        self.assertTrue(res_data.get("success"))

        incident.refresh_from_db()
        self.assertTrue(incident.group_notified)
        notif = Notification.objects.filter(group=group).latest('created_at')
        self.assertIn(group.name, notif.title)
