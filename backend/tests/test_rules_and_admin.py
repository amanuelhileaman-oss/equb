import pytest
from datetime import date
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.rules.models import RuleVersion, RuleApproval
from apps.subscriptions.models import SaasPlan, OrganizerSubscription, SubscriptionInvoice
from apps.subscriptions.services import ensure_default_plans
from apps.audit_app.models import AuditLog

@pytest.mark.django_db
class TestRulesAndAdmin:
    @pytest.fixture(autouse=True)
    def setup(self):
        ensure_permissions_seeded()
        ensure_default_plans()
        self.client = APIClient()

        self.admin = User.objects.create_user(
            email="admin_rules@digitalequb.et",
            password="AdminPassword123!",
            full_name="Admin Boss",
            is_platform_admin=True,
            is_staff=True
        )

        self.organizer = User.objects.create_user(
            email="org_rules@digitalequb.et",
            password="Password123!",
            full_name="Organizer Abebe"
        )

        self.member1 = User.objects.create_user(
            email="m1_rules@digitalequb.et",
            password="Password123!",
            full_name="Member One"
        )

        self.member2 = User.objects.create_user(
            email="m2_rules@digitalequb.et",
            password="Password123!",
            full_name="Member Two"
        )

        self.group = EqubGroup.objects.create(
            name="Rules Governance Equb",
            organizer=self.organizer,
            status=EqubGroup.GroupStatus.ACTIVE,
            currency="ETB",
            contribution_amount=Decimal("1500.00"),
            start_date=date.today(),
            rules_approval_threshold_percent=100
        )

        org_role = GroupRole.objects.get(group=None, code="GROUP_ORGANIZER")
        mem_role = GroupRole.objects.get(group=None, code="GROUP_MEMBER")

        self.m_org = GroupMembership.objects.create(group=self.group, user=self.organizer, status=GroupMembership.MembershipStatus.ACTIVE)
        MembershipRoleAssignment.objects.create(membership=self.m_org, role=org_role)

        self.m1 = GroupMembership.objects.create(group=self.group, user=self.member1, status=GroupMembership.MembershipStatus.ACTIVE)
        MembershipRoleAssignment.objects.create(membership=self.m1, role=mem_role)

        self.m2 = GroupMembership.objects.create(group=self.group, user=self.member2, status=GroupMembership.MembershipStatus.ACTIVE)
        MembershipRoleAssignment.objects.create(membership=self.m2, role=mem_role)

    def test_rule_proposal_and_unanimous_voting_activation(self):
        # 1. Organizer proposes rule version 2
        self.client.force_authenticate(user=self.organizer)
        res = self.client.post(f"/api/v1/groups/{self.group.id}/rules/", {
            "title": "Charter Amendment 2",
            "terms_text": "Contribution increased to 2,000 ETB monthly.",
            "contribution_amount": "2000.00",
            "contribution_frequency": "MONTHLY",
            "payout_method": "ROTATION_ORDER",
            "approval_threshold_percent": 100
        }, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        rule_id = res.data["id"]
        rule_v2 = RuleVersion.objects.get(id=rule_id)
        assert rule_v2.version_number == 1 or rule_v2.version_number == 2
        # Organizer automatically voted YES, but 1 of 3 active members is not 100%
        assert rule_v2.status == RuleVersion.RuleStatus.PROPOSED

        # 2. Member 1 votes APPROVED
        self.client.force_authenticate(user=self.member1)
        res_v1 = self.client.post(f"/api/v1/rules/{rule_id}/vote/", {"decision": "APPROVED"}, format="json")
        assert res_v1.status_code == status.HTTP_200_OK
        rule_v2.refresh_from_db()
        assert rule_v2.status == RuleVersion.RuleStatus.PROPOSED

        # 3. Member 2 votes APPROVED (reaching 100%)
        self.client.force_authenticate(user=self.member2)
        res_v2 = self.client.post(f"/api/v1/rules/{rule_id}/vote/", {"decision": "APPROVED"}, format="json")
        assert res_v2.status_code == status.HTTP_200_OK
        assert res_v2.data["evaluation"]["approved"] is True
        rule_v2.refresh_from_db()
        assert rule_v2.status == RuleVersion.RuleStatus.APPROVED
        assert rule_v2.effective_at is not None

        # Verify group configuration updated
        self.group.refresh_from_db()
        assert self.group.active_rules_version == rule_v2
        assert self.group.contribution_amount == Decimal("2000.00")

    def test_super_admin_metrics_revenue_isolation(self):
        # Create a SaaS subscription invoice
        plan = SaasPlan.objects.get(code="GROWTH_EQUB")
        sub = OrganizerSubscription.objects.create(
            organizer=self.organizer,
            plan=plan,
            status=OrganizerSubscription.SubscriptionStatus.ACTIVE,
            expires_at=date.today()
        )
        SubscriptionInvoice.objects.create(
            subscription=sub,
            invoice_number="INV-TEST-001",
            amount_etb=Decimal("600.00"),
            due_date=date.today(),
            status=SubscriptionInvoice.InvoiceStatus.PAID,
            paid_at=date.today()
        )

        self.client.force_authenticate(user=self.admin)
        res = self.client.get("/api/v1/admin/dashboard/")
        assert res.status_code == status.HTTP_200_OK
        assert Decimal(str(res.data["saas_subscription_revenue_etb"])) == Decimal("600.00")

    def test_super_admin_user_suspension_with_reason(self):
        self.client.force_authenticate(user=self.admin)
        res = self.client.post(f"/api/v1/admin/users/{self.member1.id}/action/", {
            "action": "SUSPEND",
            "reason": "Investigation of suspicious activity."
        }, format="json")
        assert res.status_code == status.HTTP_200_OK
        self.member1.refresh_from_db()
        assert self.member1.account_status == User.AccountStatus.SUSPENDED
        assert "Investigation" in self.member1.suspension_reason
        assert AuditLog.objects.filter(action="ADMIN_USER_SUSPENDED", target_id=str(self.member1.id)).exists()
