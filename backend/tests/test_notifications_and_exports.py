import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.models import GroupRole
from apps.contributions.models import ContributionPeriod, ContributionObligation
from apps.ledger.models import LedgerEntry
from apps.notifications.models import Notification
from apps.notifications.services import create_notification

@pytest.mark.django_db
class TestNotificationsAndExports:

    @pytest.fixture(autouse=True)
    def setup_entities(self):
        self.client = APIClient()
        self.password = "SecTestPass123!"

        self.treasurer = User.objects.create_user(
            email="export_treasurer@digitalequb.et",
            password=self.password,
            full_name="Tesfaye Export Treasurer",
            preferred_language="en"
        )
        self.member = User.objects.create_user(
            email="notif_member@digitalequb.et",
            password=self.password,
            full_name="Abebe Notif Member",
            preferred_language="am"
        )

        self.group = EqubGroup.objects.create(
            name="Exports & Alerts Equb",
            organizer=self.treasurer,
            contribution_amount=Decimal('1000.00'),
            contribution_frequency='MONTHLY',
            capacity=10,
            start_date="2026-11-01",
            status=EqubGroup.GroupStatus.ACTIVE
        )

        # Memberships
        self.m_treasurer = GroupMembership.objects.create(
            group=self.group,
            user=self.treasurer,
            status=GroupMembership.MembershipStatus.ACTIVE
        )
        self.m_member = GroupMembership.objects.create(
            group=self.group,
            user=self.member,
            status=GroupMembership.MembershipStatus.ACTIVE
        )

        # Seed period & obligation
        self.period = ContributionPeriod.objects.create(
            group=self.group,
            period_number=1,
            start_date="2026-11-01",
            due_date="2026-11-30"
        )
        self.ob = ContributionObligation.objects.create(
            group=self.group,
            period=self.period,
            membership=self.m_member,
            expected_amount=Decimal('1000.00'),
            currency='ETB',
            due_date="2026-11-05"
        )

        # Seed ledger entry
        self.ledger = LedgerEntry.objects.create(
            group=self.group,
            entry_type=LedgerEntry.EntryType.CONTRIBUTION_RECEIVED,
            direction=LedgerEntry.Direction.CREDIT,
            amount=Decimal('1000.00'),
            currency='ETB',
            reason="Initial test credit"
        )

    def test_in_app_notification_creation_and_mark_read(self):
        """Verify notification generation, unread counter, and mark-as-read transitions."""
        # 1. Generate notification
        notif = create_notification(
            user=self.member,
            group=self.group,
            title="Contribution Reminder",
            title_am="የመዋጮ ማሳሰቢያ",
            message="Your contribution of 1,000.00 ETB is due soon.",
            message_am="የ1,000.00 ብር መዋጮዎ የክፍያ ቀን ደርሷል።",
            notification_type=Notification.NotificationType.CONTRIBUTION_DUE
        )
        assert notif is not None
        assert notif.is_read is False

        # 2. Fetch via API
        self.client.force_authenticate(user=self.member)
        res = self.client.get('/api/v1/notifications/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['unread_count'] >= 1
        assert any(item['id'] == str(notif.id) for item in res.data['results'])

        # 3. Mark as read
        mark_res = self.client.post(f'/api/v1/notifications/{notif.id}/mark-read/')
        assert mark_res.status_code == status.HTTP_200_OK

        # 4. Confirm unread count decreased
        res_after = self.client.get('/api/v1/notifications/')
        updated_item = next(item for item in res_after.data['results'] if item['id'] == str(notif.id))
        assert updated_item['is_read'] is True

    def test_ledger_and_obligation_csv_exports(self):
        """Verify CSV export responses deliver valid text/csv content with correct headers."""
        self.client.force_authenticate(user=self.treasurer)

        # Ledger CSV Export
        res_ledger = self.client.get(f'/api/v1/groups/{self.group.id}/export/ledger/')
        assert res_ledger.status_code == status.HTTP_200_OK
        assert 'text/csv' in res_ledger.headers['Content-Type']
        content_ledger = res_ledger.content.decode('utf-8')
        assert "Entry ID" in content_ledger
        assert "Running Balance (ETB)" in content_ledger
        assert "1000.00" in content_ledger

        # Obligations CSV Export
        res_ob = self.client.get(f'/api/v1/groups/{self.group.id}/export/obligations/')
        assert res_ob.status_code == status.HTTP_200_OK
        assert 'text/csv' in res_ob.headers['Content-Type']
        content_ob = res_ob.content.decode('utf-8')
        assert "Member Name" in content_ob
        assert "Abebe Notif Member" in content_ob
        assert "1000.00" in content_ob
