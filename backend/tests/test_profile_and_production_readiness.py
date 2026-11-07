"""
Unit tests for User Profile Updates, Email Immutability, Password & Photo Management,
Super Admin Authentication, and Complete Ethiopian Bank Directory.
"""
from django.test import TestCase
from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.payments.chapa import ChapaClient


class ProfileAndProductionReadinessUnitTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        ensure_permissions_seeded()

        # 1. Super Admin User
        self.super_admin = User.objects.create_user(
            email='aman@gmail.com',
            password='amanuel1221',
            full_name='AMANUEL HAILIE',
            is_platform_admin=True,
            is_superuser=True,
            is_staff=True,
            preferred_language='en'
        )

        # 2. Organizer User
        self.organizer = User.objects.create_user(
            email='organizer_test@digitalequb.et',
            password='Password123!',
            full_name='Test Organizer',
            preferred_language='am'
        )
        self.group = EqubGroup.objects.create(
            name='Test Group',
            organizer=self.organizer,
            contribution_amount=5000,
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=10,
            start_date=timezone.now().date(),
            lottery_method=EqubGroup.LotteryMethod.METHOD_A,
            grace_period_days=3
        )

        # 3. Treasurer User
        self.treasurer = User.objects.create_user(
            email='treasurer_test@digitalequb.et',
            password='Password123!',
            full_name='Test Treasurer',
            preferred_language='en'
        )
        treas_role = GroupRole.objects.get(group=None, code="GROUP_TREASURER")
        treas_mem = GroupMembership.objects.create(
            user=self.treasurer,
            group=self.group,
            status=GroupMembership.MembershipStatus.ACTIVE
        )
        MembershipRoleAssignment.objects.create(membership=treas_mem, role=treas_role)

        # 4. Member User
        self.member = User.objects.create_user(
            email='member_test@digitalequb.et',
            password='Password123!',
            full_name='Chala Bekele',
            preferred_language='am'
        )
        GroupMembership.objects.create(
            user=self.member,
            group=self.group,
            status=GroupMembership.MembershipStatus.ACTIVE
        )

    # =========================================================================
    # 1. SUPER ADMIN AUTHENTICATION
    # =========================================================================
    def test_01_super_admin_credentials_authenticate(self):
        """Verify aman@gmail.com authenticates with amanuel1221 and holds platform admin status."""
        user = authenticate(email='aman@gmail.com', password='amanuel1221')
        self.assertIsNotNone(user, "Super Admin credentials failed authentication!")
        self.assertTrue(user.is_platform_admin)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.email, 'aman@gmail.com')

    def test_02_super_admin_wrong_password_fails(self):
        """Verify wrong password fails authentication."""
        user = authenticate(email='aman@gmail.com', password='wrongpassword!')
        self.assertIsNone(user)

    # =========================================================================
    # 2. EMAIL IMMUTABILITY (ALL 4 ROLES CANNOT CHANGE EMAIL)
    # =========================================================================
    def test_03_super_admin_cannot_change_email(self):
        """Super Admin cannot modify email address via profile endpoint."""
        self.client.force_authenticate(user=self.super_admin)
        resp = self.client.patch('/api/v1/auth/me/', {'email': 'hacker@example.com'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.email, 'aman@gmail.com')

    def test_04_organizer_cannot_change_email(self):
        """Organizer cannot modify email address via profile endpoint."""
        self.client.force_authenticate(user=self.organizer)
        resp = self.client.patch('/api/v1/auth/me/', {'email': 'new_org@example.com'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.organizer.refresh_from_db()
        self.assertEqual(self.organizer.email, 'organizer_test@digitalequb.et')

    def test_05_treasurer_cannot_change_email(self):
        """Treasurer cannot modify email address via profile endpoint."""
        self.client.force_authenticate(user=self.treasurer)
        resp = self.client.patch('/api/v1/auth/me/', {'email': 'new_treas@example.com'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.treasurer.refresh_from_db()
        self.assertEqual(self.treasurer.email, 'treasurer_test@digitalequb.et')

    def test_06_member_cannot_change_email(self):
        """Member cannot modify email address via member profile endpoint."""
        self.client.force_authenticate(user=self.member)
        resp = self.client.patch('/api/v1/member/profile/', {'email': 'new_member@example.com'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.member.refresh_from_db()
        self.assertEqual(self.member.email, 'member_test@digitalequb.et')

    # =========================================================================
    # 3. PHOTO (AVATAR) UPLOAD & PREVIEW FOR ALL 4 ROLES
    # =========================================================================
    def test_07_avatar_upload_super_admin(self):
        """Super admin can update photo avatar."""
        self.client.force_authenticate(user=self.super_admin)
        avatar_data = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD'
        resp = self.client.patch('/api/v1/auth/me/', {'avatar': avatar_data})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.super_admin.refresh_from_db()
        self.assertEqual(self.super_admin.avatar, avatar_data)

    def test_08_avatar_upload_member(self):
        """Member can update photo avatar without internal server error."""
        self.client.force_authenticate(user=self.member)
        avatar_data = 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD'
        resp = self.client.patch('/api/v1/member/profile/', {'avatar': avatar_data})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertEqual(self.member.avatar, avatar_data)

    # =========================================================================
    # 4. PASSWORD UPDATE WITH MINIMUM 8 CHARACTERS & VERIFICATION
    # =========================================================================
    def test_09_password_update_success(self):
        """User can change password when providing valid current and new password."""
        self.client.force_authenticate(user=self.member)
        resp = self.client.post('/api/v1/member/profile/', {
            'old_password': 'Password123!',
            'new_password': 'BrandNewPassword888'
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password('BrandNewPassword888'))

    def test_10_password_update_too_short_fails(self):
        """Password shorter than 8 characters is rejected."""
        self.client.force_authenticate(user=self.member)
        resp = self.client.post('/api/v1/member/profile/', {
            'old_password': 'Password123!',
            'new_password': 'short'
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_11_password_update_wrong_old_password_fails(self):
        """Password change fails if old password does not match."""
        self.client.force_authenticate(user=self.member)
        resp = self.client.post('/api/v1/member/profile/', {
            'old_password': 'IncorrectOldPassword!',
            'new_password': 'BrandNewPassword888'
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # 5. LANGUAGE SUPPORT ACROSS ALL 4 LANGUAGES (EN, AM, OM, TI)
    # =========================================================================
    def test_12_all_four_languages_supported(self):
        """Verify preferred_language supports English, Amharic, Oromo, and Tigrinya."""
        self.client.force_authenticate(user=self.member)
        for lang in ['en', 'am', 'om', 'ti']:
            resp = self.client.patch('/api/v1/member/profile/', {'preferred_language': lang})
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.member.refresh_from_db()
            self.assertEqual(self.member.preferred_language, lang)

    # =========================================================================
    # 6. BLANK PHONE NUMBER INTEGRITY (DOES NOT VIOLATE UNIQUE CONSTRAINT)
    # =========================================================================
    def test_13_blank_phone_number_saved_as_null(self):
        """Blank phone number string must be stored as NULL to allow multiple users without phones."""
        self.client.force_authenticate(user=self.organizer)
        resp = self.client.patch('/api/v1/auth/me/', {'phone_number': '   '})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.organizer.refresh_from_db()
        self.assertIsNone(self.organizer.phone_number)

        self.client.force_authenticate(user=self.member)
        resp2 = self.client.patch('/api/v1/member/profile/', {'phone_number': ''})
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.member.refresh_from_db()
        self.assertIsNone(self.member.phone_number)

    # =========================================================================
    # 7. COMPLETE ETHIOPIAN BANKS DIRECTORY (30 BANKS & WALLETS)
    # =========================================================================
    def test_14_chapa_banks_directory_has_all_30_institutions(self):
        """ChapaClient must return the complete list of 30 Ethiopian commercial banks & mobile wallets."""
        client = ChapaClient()
        banks = client.get_supported_banks()
        self.assertGreaterEqual(len(banks), 30)

        bank_names = [b['name'].lower() for b in banks]
        # Verify major commercial banks
        self.assertTrue(any('commercial bank of ethiopia' in name for name in bank_names))
        self.assertTrue(any('awash' in name for name in bank_names))
        self.assertTrue(any('dashen' in name for name in bank_names))
        self.assertTrue(any('abyssinia' in name for name in bank_names))
        self.assertTrue(any('wegagen' in name for name in bank_names))
        self.assertTrue(any('siinqee' in name for name in bank_names))

        # Verify digital wallets & mobile money
        self.assertTrue(any('telebirr' in name for name in bank_names))
        self.assertTrue(any('cbebirr' in name for name in bank_names))
        self.assertTrue(any('m-pesa' in name for name in bank_names))
        self.assertTrue(any('yayawallet' in name for name in bank_names))
