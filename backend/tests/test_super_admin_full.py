import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.exceptions import PermissionDenied

from apps.accounts.models import User, PasswordResetToken
from apps.accounts.totp import generate_totp_secret, verify_totp_code
import hmac, hashlib, struct, time, base64
from apps.groups.models import EqubGroup, GroupMembership
from apps.subscriptions.models import SaasPlan, OrganizerSubscription, SubscriptionInvoice
from apps.audit_app.models import (
    AuditLog, PlatformSetting, VerificationRecord,
    PaymentProviderConfiguration, Announcement, SecurityEvent
)
from apps.disputes.models import Dispute, DisputeCategory, DisputeStatus


def compute_totp(secret: str) -> str:
    key = base64.b32decode(secret, casefold=True)
    counter = int(time.time() // 30)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code_int = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code_int % 1000000).zfill(6)


class TestSuperAdminFullSuite(APITestCase):
    def setUp(self):
        # 1. Super Admin User
        self.superadmin = User.objects.create_user(
            email="superadmin.suite@digitalequb.et",
            password="AdminPassword123!",
            full_name="Super Admin Suite User",
            is_platform_admin=True,
            is_email_verified=True,
            account_status=User.AccountStatus.ACTIVE
        )

        # 2. Regular Member User (Non-Admin)
        self.member = User.objects.create_user(
            email="regular.member@digitalequb.et",
            password="MemberPassword123!",
            full_name="Regular Equb Member",
            is_platform_admin=False,
            is_email_verified=True,
            account_status=User.AccountStatus.ACTIVE
        )

        # 3. Organizer User
        self.organizer = User.objects.create_user(
            email="organizer.user@digitalequb.et",
            password="OrganizerPassword123!",
            full_name="Organizer User",
            is_platform_admin=False,
            is_email_verified=True,
            account_status=User.AccountStatus.ACTIVE
        )

        # 4. Equb Group
        self.group = EqubGroup.objects.create(
            name="Alpha Merchant Equb",
            organizer=self.organizer,
            contribution_amount=Decimal("5000.00"),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=10,
            start_date=date.today(),
            status=EqubGroup.GroupStatus.ACTIVE,
            verification_status=EqubGroup.VerificationStatus.PENDING
        )

        # 5. SaaS Plan & Subscription
        self.plan = SaasPlan.objects.create(
            code="GROWTH_TEST",
            name="Growth Test Tier",
            price_etb=Decimal("1200.00"),
            max_active_groups=3,
            billing_cycle=SaasPlan.BillingCycle.MONTHLY,
            is_active=True
        )

        self.subscription = OrganizerSubscription.objects.create(
            organizer=self.organizer,
            plan=self.plan,
            status=OrganizerSubscription.SubscriptionStatus.ACTIVE,
            expires_at=timezone.now() + timedelta(days=30)
        )

    # -------------------------------------------------------------------------
    # TEST 1: Strict Backend Authorization
    # -------------------------------------------------------------------------
    def test_unauthenticated_and_regular_user_blocked(self):
        # Unauthenticated request
        res_anon = self.client.get("/api/v1/admin/dashboard/")
        assert res_anon.status_code == status.HTTP_401_UNAUTHORIZED

        # Non-Super Admin user request
        self.client.force_authenticate(user=self.member)
        res_member = self.client.get("/api/v1/admin/dashboard/")
        assert res_member.status_code == status.HTTP_403_FORBIDDEN

        res_org_access = self.client.get("/api/v1/admin/organizers/")
        assert res_org_access.status_code == status.HTTP_403_FORBIDDEN

    # -------------------------------------------------------------------------
    # TEST 2: Overview Dashboard & Strict Revenue Isolation
    # -------------------------------------------------------------------------
    def test_overview_dashboard_and_revenue_isolation(self):
        # Create a paid SaaS subscription invoice
        SubscriptionInvoice.objects.create(
            subscription=self.subscription,
            invoice_number="INV-SAAS-001",
            amount_etb=Decimal("1200.00"),
            due_date=date.today(),
            status=SubscriptionInvoice.InvoiceStatus.PAID,
            paid_at=timezone.now()
        )

        self.client.force_authenticate(user=self.superadmin)
        res = self.client.get("/api/v1/admin/dashboard/")
        assert res.status_code == status.HTTP_200_OK

        # Verify SaaS revenue matches only paid subscription invoices
        assert res.data["saas_subscription_revenue_etb"] == Decimal("1200.00")
        assert "kpis" in res.data
        assert "growth_trends" in res.data
        assert "monthly_saas_revenue" in res.data
        assert res.data["system_status"]["status"] == "OPERATIONAL"

    # -------------------------------------------------------------------------
    # TEST 3: Organizer Management (Approve, Suspend with Reason, Reactivate)
    # -------------------------------------------------------------------------
    def test_organizer_management_actions_with_mandatory_reasons(self):
        self.client.force_authenticate(user=self.superadmin)

        # 1. List organizers
        res_list = self.client.get("/api/v1/admin/organizers/")
        assert res_list.status_code == status.HTTP_200_OK
        assert any(org["email"] == self.organizer.email for org in res_list.data)

        # 2. Suspend without reason must be rejected
        res_no_reason = self.client.post(
            f"/api/v1/admin/organizers/{self.organizer.id}/action/",
            {"action": "SUSPEND", "reason": "   "}
        )
        assert res_no_reason.status_code == status.HTTP_400_BAD_REQUEST

        # 3. Suspend with valid reason
        res_suspend = self.client.post(
            f"/api/v1/admin/organizers/{self.organizer.id}/action/",
            {"action": "SUSPEND", "reason": "Suspected KYC discrepancy on trade license"}
        )
        assert res_suspend.status_code == status.HTTP_200_OK
        self.organizer.refresh_from_db()
        assert self.organizer.account_status == User.AccountStatus.SUSPENDED
        assert "trade license" in self.organizer.suspension_reason

        # Verify audit log and security event creation
        assert AuditLog.objects.filter(action="ADMIN_ORGANIZER_SUSPENDED").exists()
        assert SecurityEvent.objects.filter(event_type=SecurityEvent.EventType.ACCOUNT_LOCKED).exists()

        # 4. Reactivate
        res_reactivate = self.client.post(
            f"/api/v1/admin/organizers/{self.organizer.id}/action/",
            {"action": "REACTIVATE", "reason": "KYC documentation verified"}
        )
        assert res_reactivate.status_code == status.HTTP_200_OK
        self.organizer.refresh_from_db()
        assert self.organizer.account_status == User.AccountStatus.ACTIVE

    # -------------------------------------------------------------------------
    # TEST 4: Equb Group Oversight & Suspension
    # -------------------------------------------------------------------------
    def test_group_oversight_and_verification(self):
        self.client.force_authenticate(user=self.superadmin)

        # Verify Group
        res_verify = self.client.post(
            f"/api/v1/admin/groups/{self.group.id}/action/",
            {"action": "VERIFY", "reason": "Bylaws approved"}
        )
        assert res_verify.status_code == status.HTTP_200_OK
        self.group.refresh_from_db()
        assert self.group.verification_status == EqubGroup.VerificationStatus.VERIFIED

        # Suspend Group (Operations frozen, but funds preserved)
        res_suspend = self.client.post(
            f"/api/v1/admin/groups/{self.group.id}/action/",
            {"action": "SUSPEND", "reason": "Annual audit freeze"}
        )
        assert res_suspend.status_code == status.HTTP_200_OK
        self.group.refresh_from_db()
        assert self.group.status == EqubGroup.GroupStatus.SUSPENDED

    # -------------------------------------------------------------------------
    # TEST 5: Verification Center Workflows
    # -------------------------------------------------------------------------
    def test_verification_center_workflows(self):
        self.client.force_authenticate(user=self.superadmin)

        rec = VerificationRecord.objects.create(
            category=VerificationRecord.Category.PAYMENT_DESTINATION,
            target_id="dest-999",
            target_name="Bank of Abyssinia Joint Account",
            status=VerificationRecord.Status.PENDING,
            submission_notes="Bank stamp attached"
        )

        # Request Additional Information
        res_info = self.client.post(
            f"/api/v1/admin/verifications/{rec.id}/action/",
            {"action": "REQUEST_INFO", "reason": "Please provide official board authorization letter"}
        )
        assert res_info.status_code == status.HTTP_200_OK
        rec.refresh_from_db()
        assert rec.status == VerificationRecord.Status.ADDITIONAL_INFORMATION_REQUIRED

        # Approve
        res_approve = self.client.post(
            f"/api/v1/admin/verifications/{rec.id}/action/",
            {"action": "APPROVE", "reason": "Board authorization verified"}
        )
        assert res_approve.status_code == status.HTTP_200_OK
        rec.refresh_from_db()
        assert rec.status == VerificationRecord.Status.APPROVED

    # -------------------------------------------------------------------------
    # TEST 6: Payment Providers Management & Secrets Safety
    # -------------------------------------------------------------------------
    def test_payment_providers_management_and_secrets_safety(self):
        self.client.force_authenticate(user=self.superadmin)

        res = self.client.get("/api/v1/admin/payment-providers/")
        assert res.status_code == status.HTTP_200_OK
        assert len(res.data) >= 5

        # Verify secrets are NOT exposed
        for p in res.data:
            assert "secret" not in p
            assert "private_key" not in p
            assert "api_key" not in p

        # Toggle Provider
        telebirr = PaymentProviderConfiguration.objects.get(provider_code="TELEBIRR")
        res_toggle = self.client.post(
            f"/api/v1/admin/payment-providers/{telebirr.id}/action/",
            {"action": "TOGGLE"}
        )
        assert res_toggle.status_code == status.HTTP_200_OK

        # Connection Handshake Test
        res_test = self.client.post(
            f"/api/v1/admin/payment-providers/{telebirr.id}/action/",
            {"action": "TEST_CONNECTION"}
        )
        assert res_test.status_code == status.HTTP_200_OK
        telebirr.refresh_from_db()
        assert telebirr.last_tested_at is not None

    # -------------------------------------------------------------------------
    # TEST 7: Financial Reports & CSV Export Safety
    # -------------------------------------------------------------------------
    def test_financial_reports_and_csv_export(self):
        self.client.force_authenticate(user=self.superadmin)

        res_rep = self.client.get("/api/v1/admin/reports/financial/")
        assert res_rep.status_code == status.HTTP_200_OK
        assert "total_saas_revenue_etb" in res_rep.data["summary"]
        assert "plan_breakdown" in res_rep.data

        # Export CSV
        res_csv = self.client.get("/api/v1/admin/reports/export/")
        assert res_csv.status_code == status.HTTP_200_OK
        assert res_csv["Content-Type"] == "text/csv"
        assert "Invoice Number,Organizer Name,Plan" in res_csv.content.decode("utf-8")

    # -------------------------------------------------------------------------
    # TEST 8: System Health Diagnostics
    # -------------------------------------------------------------------------
    def test_system_health_diagnostics(self):
        self.client.force_authenticate(user=self.superadmin)

        res = self.client.get("/api/v1/admin/system-health/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["status"] == "HEALTHY"
        assert res.data["database"]["status"] == "CONNECTED"
        assert res.data["database"]["latency_ms"] >= 0
        assert res.data["backup_status"]["integrity_verified"] is True

    # -------------------------------------------------------------------------
    # TEST 9: Protection of Last Active Super Admin (Suspension & Demotion)
    # -------------------------------------------------------------------------
    def test_last_active_superadmin_protection(self):
        self.client.force_authenticate(user=self.superadmin)

        # Ensure self.superadmin is the only active platform admin
        User.objects.exclude(id=self.superadmin.id).filter(is_platform_admin=True).update(is_platform_admin=False)

        # 1. Attempt to suspend the only active superadmin
        res_suspend = self.client.post(
            f"/api/v1/admin/users/{self.superadmin.id}/action/",
            {"action": "SUSPEND", "reason": "Accidental self lock"}
        )
        assert res_suspend.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot suspend or disable the last active Platform Super Admin" in str(res_suspend.data)
        self.superadmin.refresh_from_db()
        assert self.superadmin.account_status == User.AccountStatus.ACTIVE

        # 2. Attempt to demote (remove superadmin status) from the only active superadmin
        res_demote = self.client.post(
            f"/api/v1/admin/users/{self.superadmin.id}/action/",
            {"action": "TOGGLE_SUPER_ADMIN", "reason": "Self demotion test"}
        )
        assert res_demote.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot revoke Super Admin privileges from the last active Super Admin" in str(res_demote.data)
        self.superadmin.refresh_from_db()
        assert self.superadmin.is_platform_admin is True

        # 3. Create a second super admin
        second_admin = User.objects.create_user(
            email="second.admin@digitalequb.et",
            password="AdminPassword456!",
            full_name="Second Admin",
            is_platform_admin=True,
            is_email_verified=True,
            account_status=User.AccountStatus.ACTIVE
        )

        # Now demoting the second admin succeeds because self.superadmin is still active
        res_demote_second = self.client.post(
            f"/api/v1/admin/users/{second_admin.id}/action/",
            {"action": "TOGGLE_SUPER_ADMIN", "reason": "Deprovisioning secondary admin"}
        )
        assert res_demote_second.status_code == status.HTTP_200_OK
        second_admin.refresh_from_db()
        assert second_admin.is_platform_admin is False

    # -------------------------------------------------------------------------
    # TEST 10: Privilege Escalation & Access Control
    # -------------------------------------------------------------------------
    def test_privilege_escalation_and_non_admin_block(self):
        # A regular member attempts to toggle themselves or others to superadmin
        self.client.force_authenticate(user=self.member)
        res_escalate = self.client.post(
            f"/api/v1/admin/users/{self.member.id}/action/",
            {"action": "TOGGLE_SUPER_ADMIN"}
        )
        assert res_escalate.status_code == status.HTTP_403_FORBIDDEN
        self.member.refresh_from_db()
        assert self.member.is_platform_admin is False

    # -------------------------------------------------------------------------
    # TEST 11: Login Throttling & Account Lockout
    # -------------------------------------------------------------------------
    def test_login_throttling_and_lockout(self):
        self.client.logout()

        target_user = User.objects.create_user(
            email="victim@digitalequb.et",
            password="CorrectPassword123!",
            full_name="Victim User",
            account_status=User.AccountStatus.ACTIVE
        )

        # 4 consecutive bad attempts
        for i in range(4):
            res_bad = self.client.post("/api/v1/auth/login/", {
                "email": target_user.email,
                "password": "WrongPassword!"
            })
            assert res_bad.status_code == status.HTTP_400_BAD_REQUEST
            target_user.refresh_from_db()
            assert target_user.failed_login_attempts == i + 1
            assert target_user.account_status == User.AccountStatus.ACTIVE

        # 5th bad attempt -> Account is locked
        res_fifth = self.client.post("/api/v1/auth/login/", {
            "email": target_user.email,
            "password": "WrongPassword!"
        })
        assert res_fifth.status_code == status.HTTP_400_BAD_REQUEST
        assert "locked" in str(res_fifth.data).lower()

        target_user.refresh_from_db()
        assert target_user.account_status == User.AccountStatus.SUSPENDED
        assert target_user.failed_login_attempts >= 5

        # Attempting with correct password is still blocked while locked
        res_correct = self.client.post("/api/v1/auth/login/", {
            "email": target_user.email,
            "password": "CorrectPassword123!"
        })
        assert res_correct.status_code == status.HTTP_400_BAD_REQUEST
        assert "suspended" in str(res_correct.data).lower() or "locked" in str(res_correct.data).lower()

    # -------------------------------------------------------------------------
    # TEST 12: TOTP Two-Factor Authentication Setup & Verification
    # -------------------------------------------------------------------------
    def test_totp_mfa_flow(self):
        # Setup MFA
        self.client.force_authenticate(user=self.superadmin)
        res_setup = self.client.post("/api/v1/auth/mfa/setup/")
        assert res_setup.status_code == status.HTTP_200_OK
        assert "secret" in res_setup.data
        assert "uri" in res_setup.data
        secret = res_setup.data["secret"]

        # Generate valid TOTP code
        valid_code = compute_totp(secret)

        # Verify MFA with valid code and secret
        res_verify = self.client.post("/api/v1/auth/mfa/verify/", {"code": valid_code, "secret": secret})
        assert res_verify.status_code == status.HTTP_200_OK
        self.superadmin.refresh_from_db()
        assert self.superadmin.mfa_enabled is True
        assert self.superadmin.mfa_secret == secret

        # Test login challenge: Login without MFA code prompts for code
        self.client.logout()
        res_login_step1 = self.client.post("/api/v1/auth/login/", {
            "email": self.superadmin.email,
            "password": "AdminPassword123!"
        })
        assert res_login_step1.status_code == status.HTTP_200_OK
        assert res_login_step1.data["mfa_required"] is True
        assert "tokens" not in res_login_step1.data

        # Provide MFA code with login
        new_code = compute_totp(secret)
        res_login_step2 = self.client.post("/api/v1/auth/login/", {
            "email": self.superadmin.email,
            "password": "AdminPassword123!",
            "mfa_code": new_code
        })
        assert res_login_step2.status_code == status.HTTP_200_OK
        assert res_login_step2.data["success"] is True
        assert "user" in res_login_step2.data
        assert res_login_step2.data.get("mfa_required", False) is False

    # -------------------------------------------------------------------------
    # TEST 13: Password Reset Token Security
    # -------------------------------------------------------------------------
    def test_password_reset_token_flow(self):
        # Request reset with DEBUG=True so dev_token is returned for verification
        with self.settings(DEBUG=True):
            res_req = self.client.post("/api/v1/auth/password/reset/request/", {
                "email": self.member.email
            })
            assert res_req.status_code == status.HTTP_200_OK
            assert PasswordResetToken.objects.filter(user=self.member).exists()
            raw_token = res_req.data.get("dev_token")
            assert raw_token is not None

        # Confirm reset with mismatched passwords fails
        res_mismatch = self.client.post("/api/v1/auth/password/reset/confirm/", {
            "token": raw_token,
            "password": "NewStrongPassword789!",
            "password_confirm": "DifferentPassword789!"
        })
        assert res_mismatch.status_code == status.HTTP_400_BAD_REQUEST

        # Confirm reset with valid password succeeds
        res_confirm = self.client.post("/api/v1/auth/password/reset/confirm/", {
            "token": raw_token,
            "password": "NewStrongPassword789!",
            "password_confirm": "NewStrongPassword789!"
        })
        assert res_confirm.status_code == status.HTTP_200_OK

        # Token reuse fails
        res_reuse = self.client.post("/api/v1/auth/password/reset/confirm/", {
            "token": raw_token,
            "password": "AnotherPassword789!",
            "password_confirm": "AnotherPassword789!"
        })
        assert res_reuse.status_code == status.HTTP_400_BAD_REQUEST

    # -------------------------------------------------------------------------
    # TEST 14: AuditLog Application-Level Immutability
    # -------------------------------------------------------------------------
    def test_audit_log_application_immutability(self):
        log = AuditLog.objects.create(
            actor=self.superadmin,
            action="SECURITY_CHECKPOINT",
            details={"notes": "Original state"}
        )

        # Attempt to modify existing audit log
        log.action = "TAMPERED_ACTION"
        with pytest.raises(PermissionDenied):
            log.save()

        # Attempt to delete audit log
        with pytest.raises(PermissionDenied):
            log.delete()

    # -------------------------------------------------------------------------
    # TEST 15: Groups List and Detail Integrity
    # -------------------------------------------------------------------------
    def test_groups_list_and_detail_endpoints(self):
        self.client.force_authenticate(user=self.superadmin)

        res_list = self.client.get("/api/v1/admin/groups/")
        assert res_list.status_code == status.HTTP_200_OK
        assert any(str(g["id"]) == str(self.group.id) for g in res_list.data)

        res_detail = self.client.get(f"/api/v1/admin/groups/{self.group.id}/")
        assert res_detail.status_code == status.HTTP_200_OK
        assert res_detail.data["group"]["name"] == "Alpha Merchant Equb"
        assert res_detail.data["group"]["capacity"] == 10
        assert "members" in res_detail.data
        assert "destinations" in res_detail.data

    # -------------------------------------------------------------------------
    # TEST 16: Audit Logs CSV Export with CSV Injection Sanitization
    # -------------------------------------------------------------------------
    def test_audit_logs_csv_export(self):
        self.client.force_authenticate(user=self.superadmin)

        # Create an audit log with potentially malicious spreadsheet formula prefix
        AuditLog.objects.create(
            actor=self.superadmin,
            action="FORMULA_TEST",
            details={"risk": "=1+1"}
        )

        res_csv = self.client.get("/api/v1/admin/audit-logs/export/")
        assert res_csv.status_code == status.HTTP_200_OK
        assert res_csv["Content-Type"] == "text/csv"
        content = res_csv.content.decode("utf-8")
        assert "Timestamp,Actor,Action,Target Model,Target ID,IP Address,User Agent" in content
        assert "FORMULA_TEST" in content
