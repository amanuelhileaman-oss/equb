import uuid
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User, OrganizerProfile
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.models import GroupRole
from apps.audit_app.models import Announcement
from apps.notifications.models import Notification
from apps.notifications.services import (
    send_platform_notification, dispatch_announcement_fanout,
    notify_verification_decision, notify_subscription_renewal, notify_contribution_deadline
)


class NotificationsAndProfileTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            email="admin_notif@example.com",
            password="AdminPass123!",
            full_name="Admin Notification Officer"
        )
        self.organizer = User.objects.create_user(
            email="org_notif@example.com",
            password="Password123!",
            full_name="Organizer Test",
            phone_number="0911000001"
        )
        self.org_profile = OrganizerProfile.objects.create(
            user=self.organizer,
            business_name="Test Org Equb",
            business_type="PLC",
            verification_status=OrganizerProfile.VerificationStatus.PENDING_VERIFICATION,
            payment_status=OrganizerProfile.PaymentStatus.PAYMENT_CONFIRMED,
            subscription_amount=Decimal('500.00')
        )
        self.group = EqubGroup.objects.create(
            name="Alpha Equb",
            organizer=self.organizer,
            contribution_amount=Decimal('1000.00'),
            capacity=10,
            start_date=timezone.now().date()
        )
        self.member = User.objects.create_user(
            email="mem_notif@example.com",
            password="Password123!",
            full_name="Member Test",
            phone_number="0911000002"
        )
        self.membership = GroupMembership.objects.create(
            group=self.group,
            user=self.member,
            status=GroupMembership.MembershipStatus.ACTIVE
        )

    def test_superadmin_profile_and_password_update(self):
        """Verify Image 1 & 2 fixes: Super Admin can update profile and change password seamlessly."""
        self.client.force_authenticate(user=self.admin)

        # 1. Update profile without password
        res = self.client.patch("/api/v1/auth/me/", {
            "full_name": "Updated Admin Name",
            "phone_number": "0911999999",
            "preferred_language": "am"
        })
        self.assertEqual(res.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.full_name, "Updated Admin Name")
        self.assertEqual(self.admin.phone_number, "0911999999")
        self.assertEqual(self.admin.preferred_language, "am")

        # 2. Update password as authenticated platform admin
        res = self.client.patch("/api/v1/auth/me/", {
            "new_password": "NewAdminPass123!",
            "confirm_new_password": "NewAdminPass123!"
        })
        self.assertEqual(res.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("NewAdminPass123!"))

    def test_organizer_role_resolution(self):
        """Verify Image 4 fix: Organizer with profile is recognized as ORGANIZER, not MEMBER."""
        self.client.force_authenticate(user=self.organizer)
        res = self.client.get("/api/v1/auth/me/")
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.data['is_organizer'])
        self.assertEqual(res.data['primary_role'], 'ORGANIZER')
        self.assertEqual(res.data['user']['primary_role'], 'ORGANIZER')

    def test_create_and_broadcast_maintenance_announcement(self):
        """Verify creating and broadcasting a MAINTENANCE announcement."""
        self.client.force_authenticate(user=self.admin)

        res = self.client.post("/api/v1/admin/announcements/", {
            "title": "Scheduled Maintenance Alert",
            "title_am": "የታቀደ የጥገና ማስታወቂያ",
            "content": "The system will be undergoing maintenance on Sunday midnight.",
            "content_am": "እሁድ እኩለ ሌሊት ላይ የስርዓት ጥገና ይደረጋል።",
            "category": "MAINTENANCE",
            "priority": "HIGH",
            "target_audience": "ALL",
            "channels": ["IN_APP", "EMAIL", "SMS"],
            "publish_now": True
        })
        self.assertEqual(res.status_code, 201)
        self.assertGreaterEqual(res.data['recipients_notified'], 3)

        # Check in-app notification delivered to organizer and member
        notifs = Notification.objects.filter(title="Scheduled Maintenance Alert")
        self.assertGreaterEqual(notifs.count(), 3)
        self.assertTrue(notifs.filter(user=self.organizer).exists())
        self.assertTrue(notifs.filter(user=self.member).exists())

    def test_target_specific_organizer_announcement(self):
        """Verify targeting a specific organizer."""
        self.client.force_authenticate(user=self.admin)

        res = self.client.post("/api/v1/admin/announcements/", {
            "title": "Organizer Compliance Notice",
            "content": "Please verify your Ethiopian business license.",
            "category": "VERIFICATION",
            "priority": "URGENT",
            "target_audience": "SPECIFIC_ORGANIZER",
            "target_user_id": str(self.organizer.id),
            "channels": ["IN_APP", "EMAIL"],
            "publish_now": True
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['recipients_notified'], 1)

        # Only organizer should receive this notification
        self.assertTrue(Notification.objects.filter(user=self.organizer, title="Organizer Compliance Notice").exists())
        self.assertFalse(Notification.objects.filter(user=self.member, title="Organizer Compliance Notice").exists())

    def test_target_specific_group_announcement(self):
        """Verify targeting members of a specific Equb group."""
        self.client.force_authenticate(user=self.admin)

        res = self.client.post("/api/v1/admin/announcements/", {
            "title": "Alpha Equb Cycle Announcement",
            "content": "Round 1 payouts will begin tomorrow.",
            "category": "FEATURE",
            "priority": "NORMAL",
            "target_audience": "SPECIFIC_GROUP",
            "target_group_id": str(self.group.id),
            "channels": ["IN_APP"],
            "publish_now": True
        })
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['recipients_notified'], 1)

        self.assertTrue(Notification.objects.filter(user=self.member, title="Alpha Equb Cycle Announcement").exists())

    def test_automated_verification_decision_triggers(self):
        """Verify automated notifications on Super Admin verification decisions."""
        self.client.force_authenticate(user=self.admin)

        # 1. Approve
        res = self.client.post(f"/api/v1/admin/organizers/{self.organizer.id}/action/", {
            "action": "APPROVE_VERIFICATION",
            "reason": "Business license ET-2026 verified"
        })
        self.assertEqual(res.status_code, 200)
        notif = Notification.objects.filter(user=self.organizer, notification_type=Notification.NotificationType.VERIFICATION_DECISION).first()
        self.assertIsNotNone(notif)
        self.assertIn("Approved", notif.title)

        # 2. Reject
        res = self.client.post(f"/api/v1/admin/organizers/{self.organizer.id}/action/", {
            "action": "REJECT_VERIFICATION",
            "reason": "Invalid tax ID"
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(Notification.objects.filter(user=self.organizer, title__icontains="Rejected").exists())

    def test_subscription_and_contribution_deadline_helpers(self):
        """Verify automated subscription renewal and contribution deadline helpers."""
        # 1. Subscription renewal
        notify_subscription_renewal(self.organizer, "Growth Plan", "2026-12-01", "600.00")
        sub_notif = Notification.objects.filter(user=self.organizer, notification_type=Notification.NotificationType.SUBSCRIPTION_RENEWAL).first()
        self.assertIsNotNone(sub_notif)
        self.assertIn("Growth Plan", sub_notif.title)
        self.assertIn("600.00", sub_notif.message)

        # 2. Contribution deadline
        notify_contribution_deadline(self.member, self.group, "2026-11-15", "1000.00")
        contrib_notif = Notification.objects.filter(user=self.member, notification_type=Notification.NotificationType.CONTRIBUTION_DEADLINE).first()
        self.assertIsNotNone(contrib_notif)
        self.assertIn(self.group.name, contrib_notif.title)
        self.assertIn("1000.00", contrib_notif.message)

    def test_platform_settings_management(self):
        """Verify Module 13: Platform Settings retrieval, multi-category defaults, and patching."""
        self.client.force_authenticate(user=self.admin)

        # 1. GET Settings
        res = self.client.get("/api/v1/admin/settings/")
        self.assertEqual(res.status_code, 200)
        settings_map = res.data.get("settings_map", {})
        self.assertIn("GENERAL_CONFIG", settings_map)
        self.assertIn("LOCALIZATION_CONFIG", settings_map)
        self.assertIn("SECURITY_CONFIG", settings_map)
        self.assertIn("NOTIFICATION_CONFIG", settings_map)
        self.assertIn("SUBSCRIPTION_CONFIG", settings_map)
        self.assertIn("MAINTENANCE_CONFIG", settings_map)

        # 2. PATCH Single Setting (Maintenance Mode)
        res_patch = self.client.patch("/api/v1/admin/settings/", {
            "key": "MAINTENANCE_CONFIG",
            "value": {
                "maintenance_mode": True,
                "maintenance_message": "Platform upgrading to v2.0",
                "allowed_ips": ["127.0.0.1", "192.168.1.100"]
            }
        }, format='json')
        self.assertEqual(res_patch.status_code, 200)
        self.assertTrue(res_patch.data['settings_map']['MAINTENANCE_CONFIG']['maintenance_mode'])

        # 3. PATCH Batch Settings
        res_batch = self.client.patch("/api/v1/admin/settings/", {
            "settings": {
                "GENERAL_CONFIG": {
                    "platform_name": "Digital Equb Ethiopia Enterprise",
                    "support_email": "admin@digitalequb.et"
                },
                "SUBSCRIPTION_CONFIG": {
                    "default_trial_days": 21,
                    "grace_period_days": 7
                }
            }
        }, format='json')
        self.assertEqual(res_batch.status_code, 200)
        self.assertEqual(res_batch.data['settings_map']['GENERAL_CONFIG']['platform_name'], "Digital Equb Ethiopia Enterprise")
        self.assertEqual(res_batch.data['settings_map']['SUBSCRIPTION_CONFIG']['default_trial_days'], 21)

    def test_admin_system_health_telemetry(self):
        """Verify Module 14: System Health monitoring, database connectivity, and background jobs."""
        self.client.force_authenticate(user=self.admin)

        res = self.client.get("/api/v1/admin/system-health/")
        self.assertEqual(res.status_code, 200)
        data = res.data

        # Overall Status & Uptime
        self.assertIn(data['status'], ['HEALTHY', 'CRITICAL'])
        self.assertIn("uptime", data)
        self.assertIn("uptime_percentage", data['uptime'])

        # Database Connectivity
        self.assertEqual(data['database']['status'], 'CONNECTED')
        self.assertGreaterEqual(data['database']['tables_count'], 40)
        self.assertIsInstance(data['database']['latency_ms'], (int, float))

        # API Server
        self.assertEqual(data['api_server']['status'], 'OPERATIONAL')
        self.assertEqual(data['api_server']['timezone'], 'Africa/Addis_Ababa')

        # Payment Provider Connectivity
        self.assertIn("payment_integrations", data)
        self.assertGreaterEqual(data['payment_integrations']['total_configured'], 1)
        providers = data['payment_integrations']['providers']
        provider_codes = [p['code'] for p in providers]
        self.assertTrue(any(code in provider_codes for code in ['TELEBIRR', 'CBE_BIRR', 'CHAPA']))

        # Background Jobs & Workers
        self.assertEqual(data['background_jobs']['status'], 'OPERATIONAL')
        self.assertEqual(data['background_jobs']['failed_tasks_count'], 0)
        self.assertGreaterEqual(len(data['background_jobs']['task_runners']), 4)

        # Server Resources (CPU, Memory, Disk)
        self.assertIn("server_resources", data)
        self.assertIn("cpu", data['server_resources'])
        self.assertIn("memory", data['server_resources'])
        self.assertIn("disk", data['server_resources'])
        self.assertGreater(data['server_resources']['memory']['total_mb'], 0)

        # Error Logs & Security Events
        self.assertIn("error_logs", data)
        self.assertIn("total_security_events_24h", data['error_logs'])

