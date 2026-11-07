import pytest
from datetime import date
from decimal import Decimal
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.services import ensure_permissions_seeded, has_group_permission
from apps.subscriptions.services import ensure_default_plans, get_or_create_active_subscription
from apps.subscriptions.models import SaasPlan

@pytest.mark.django_db
class TestGroupsAndRoles:
    @pytest.fixture(autouse=True)
    def setup(self):
        ensure_permissions_seeded()
        ensure_default_plans()
        self.client = APIClient()

        self.organizer = User.objects.create_user(
            email="org_test@digitalequb.et",
            password="Password123!",
            full_name="Organizer Test"
        )
        self.starter_sub = get_or_create_active_subscription(self.organizer)

    def test_group_creation_within_subscription_limit(self):
        self.client.force_authenticate(user=self.organizer)
        payload = {
            "name": "Bole Business Equb",
            "description": "Weekly Equb for business owners in Bole.",
            "group_purpose": "Trade Liquidity",
            "contribution_amount": "5000.00",
            "contribution_frequency": "WEEKLY",
            "capacity": 10,
            "start_date": str(date.today()),
            "payout_method": "ROTATION_ORDER",
            "allowed_payment_methods": ["DIGITAL_PROVIDER", "CASH"],
            "rules_approval_threshold_percent": 100
        }
        res = self.client.post("/api/v1/groups/", payload, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        group = EqubGroup.objects.get(name="Bole Business Equb")
        assert group.organizer == self.organizer
        assert group.status == EqubGroup.GroupStatus.PENDING_APPROVAL
        assert group.active_rules_version is not None
        # Verify organizer automatically assigned GROUP_ORGANIZER role
        assert has_group_permission(self.organizer, group, 'group:manage')

    def test_group_creation_rejected_when_subscription_limit_exceeded(self):
        self.client.force_authenticate(user=self.organizer)
        # Create 1 group (Starter limit is 1)
        EqubGroup.objects.create(
            name="Existing Group 1",
            organizer=self.organizer,
            status=EqubGroup.GroupStatus.ACTIVE,
            start_date=date.today(),
            contribution_amount=Decimal('1000.00')
        )

        payload = {
            "name": "Excess Group 2",
            "contribution_amount": "2000.00",
            "contribution_frequency": "MONTHLY",
            "start_date": str(date.today())
        }
        res = self.client.post("/api/v1/groups/", payload, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "Subscription group limit reached" in str(res.data)

    def test_cross_group_authorization_isolation(self):
        # User in Group A cannot manage Group B
        user_a = User.objects.create_user(email="user_a@digitalequb.et", password="Password123!", full_name="User A")
        user_b = User.objects.create_user(email="user_b@digitalequb.et", password="Password123!", full_name="User B")

        group_b = EqubGroup.objects.create(
            name="Group B Private",
            organizer=user_b,
            status=EqubGroup.GroupStatus.ACTIVE,
            start_date=date.today(),
            contribution_amount=Decimal('1000.00')
        )

        self.client.force_authenticate(user=user_a)
        # Try to modify group B
        res = self.client.patch(f"/api/v1/groups/{group_b.id}/", {"name": "Hacked Group"}, format="json")
        assert res.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
