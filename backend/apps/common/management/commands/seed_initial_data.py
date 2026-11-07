from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.subscriptions.services import ensure_default_plans, get_or_create_active_subscription
from apps.audit_app.models import PlatformSetting
from apps.groups.models import EqubGroup, GroupMembership
from apps.rules.models import RuleVersion, RuleApproval
from apps.rules.services import evaluate_rule_approvals
from apps.contributions.models import ContributionPeriod, ContributionObligation
from apps.payments.models import GroupPaymentDestination

class Command(BaseCommand):
    help = "Seeds initial permissions, SaaS plans, platform settings, and verified demo accounts."

    def handle(self, *args, **options):
        self.stdout.write("1. Seeding permissions and system role templates...")
        ensure_permissions_seeded()

        self.stdout.write("2. Seeding default SaaS subscription plans...")
        ensure_default_plans()

        self.stdout.write("3. Seeding platform settings...")
        PlatformSetting.objects.get_or_create(
            key="PLATFORM_CURRENCY",
            defaults={"value": "ETB", "description": "Default platform currency"}
        )
        PlatformSetting.objects.get_or_create(
            key="LIVE_MONEY_PROCESSING_ENABLED",
            defaults={"value": False, "description": "Whether live bank/mobile money API processing is certified and enabled"}
        )
        PlatformSetting.objects.get_or_create(
            key="SUPPORTED_LANGUAGES",
            defaults={"value": ["en", "am"], "description": "Supported UI languages: English and Amharic"}
        )

        self.stdout.write("4. Seeding user accounts...")
        # Super Admin
        aman_admin, _ = User.objects.get_or_create(
            email="aman@gmail.com",
            defaults={
                "full_name": "AMANUEL HAILIE",
                "is_platform_admin": True,
                "is_staff": True,
                "is_superuser": True,
                "is_email_verified": True,
                "account_status": User.AccountStatus.ACTIVE,
                "preferred_language": "en"
            }
        )
        aman_admin.is_platform_admin = True
        aman_admin.is_staff = True
        aman_admin.is_superuser = True
        aman_admin.set_password("amanuel1221")
        aman_admin.save()

        super_admin, _ = User.objects.get_or_create(
            email="superadmin@digitalequb.et",
            defaults={
                "full_name": "Almaz Tesfaye (Platform Admin)",
                "is_platform_admin": True,
                "is_staff": True,
                "is_superuser": True,
                "is_email_verified": True,
                "account_status": User.AccountStatus.ACTIVE,
                "preferred_language": "am"
            }
        )
        super_admin.set_password("AdminPass123!")
        super_admin.save()

        # Organizer
        organizer, _ = User.objects.get_or_create(
            email="organizer@digitalequb.et",
            defaults={
                "full_name": "Dawit Kebede (Organizer)",
                "is_email_verified": True,
                "account_status": User.AccountStatus.ACTIVE,
                "preferred_language": "en"
            }
        )
        organizer.set_password("OrganizerPass123!")
        organizer.save()
        get_or_create_active_subscription(organizer)

        # Treasurer
        treasurer, _ = User.objects.get_or_create(
            email="treasurer@digitalequb.et",
            defaults={
                "full_name": "Bethlehem Haile (Treasurer)",
                "is_email_verified": True,
                "account_status": User.AccountStatus.ACTIVE,
                "preferred_language": "am"
            }
        )
        treasurer.set_password("TreasurerPass123!")
        treasurer.save()

        # Members
        member1, _ = User.objects.get_or_create(
            email="member1@digitalequb.et",
            defaults={
                "full_name": "Chala Bekele",
                "is_email_verified": True,
                "account_status": User.AccountStatus.ACTIVE,
                "preferred_language": "am"
            }
        )
        member1.set_password("MemberPass123!")
        member1.save()

        member2, _ = User.objects.get_or_create(
            email="member2@digitalequb.et",
            defaults={
                "full_name": "Sara Mohammed",
                "is_email_verified": True,
                "account_status": User.AccountStatus.ACTIVE,
                "preferred_language": "en"
            }
        )
        member2.set_password("MemberPass123!")
        member2.save()

        self.stdout.write("5. Seeding initial verified sample Equb group...")
        sample_group, created = EqubGroup.objects.get_or_create(
            name="Arada Traders Weekly Equb",
            defaults={
                "description": "Weekly rotating savings for merchants in the Arada sub-city district.",
                "group_purpose": "Business Capital & Mutual Support",
                "organizer": organizer,
                "status": EqubGroup.GroupStatus.ACTIVE,
                "verification_status": EqubGroup.VerificationStatus.VERIFIED,
                "currency": "ETB",
                "contribution_amount": Decimal("2500.00"),
                "contribution_frequency": EqubGroup.Frequency.WEEKLY,
                "capacity": 10,
                "start_date": date.today(),
                "payout_method": EqubGroup.PayoutMethod.ROTATION_ORDER,
                "allowed_payment_methods": ["DIGITAL_PROVIDER", "CASH", "BANK_TRANSFER"],
                "rules_approval_threshold_percent": 100,
                "require_cash_second_confirmation": True
            }
        )

        # Setup payment destinations
        GroupPaymentDestination.objects.get_or_create(
            group=sample_group,
            provider_or_bank="Telebirr Merchant",
            defaults={
                "account_name": "Arada Equb Group Fund",
                "account_number": "0911234567",
                "transfer_instructions": "Direct Telebirr transfer or Paybill to 0911234567. Use your full name and round number in the remarks.",
                "is_verified": True,
                "is_active": True
            }
        )
        GroupPaymentDestination.objects.get_or_create(
            group=sample_group,
            provider_or_bank="Commercial Bank of Ethiopia (CBE)",
            defaults={
                "account_name": "Arada Equb Joint Custody",
                "account_number": "1000234567890",
                "branch_or_details": "Arada Giorgis Branch",
                "transfer_instructions": "Deposit or CBE Mobile Banking transfer. Attach deposit slip or enter transaction ID.",
                "is_verified": True,
                "is_active": True
            }
        )

        # Memberships
        organizer_role = GroupRole.objects.get(group=None, code="GROUP_ORGANIZER")
        treasurer_role = GroupRole.objects.get(group=None, code="GROUP_TREASURER")
        member_role = GroupRole.objects.get(group=None, code="GROUP_MEMBER")

        # Organizer membership
        m_org, _ = GroupMembership.objects.get_or_create(
            group=sample_group,
            user=organizer,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 1, "joined_at": timezone.now()}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_org, role=organizer_role)

        # Treasurer membership
        m_tr, _ = GroupMembership.objects.get_or_create(
            group=sample_group,
            user=treasurer,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 2, "joined_at": timezone.now()}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_tr, role=treasurer_role)

        # Member 1
        m_1, _ = GroupMembership.objects.get_or_create(
            group=sample_group,
            user=member1,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 3, "joined_at": timezone.now()}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_1, role=member_role)

        # Member 2
        m_2, _ = GroupMembership.objects.get_or_create(
            group=sample_group,
            user=member2,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 4, "joined_at": timezone.now()}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_2, role=member_role)

        # Versioned Rules
        rule_v1, _ = RuleVersion.objects.get_or_create(
            group=sample_group,
            version_number=1,
            defaults={
                "title": "Arada Traders Equb Charter v1",
                "terms_text": "All members contribute 2,500 ETB weekly by Friday 5:00 PM. Payout is determined by fixed rotation order. All cash receipts require dual confirmation by Organizer or Treasurer. Disputes are resolved within 48 hours.",
                "contribution_amount": Decimal("2500.00"),
                "contribution_frequency": "WEEKLY",
                "payout_method": "ROTATION_ORDER",
                "approval_threshold_percent": 100,
                "status": RuleVersion.RuleStatus.APPROVED,
                "proposed_by": organizer,
                "effective_at": timezone.now()
            }
        )
        sample_group.active_rules_version = rule_v1
        sample_group.save()

        for m in [m_org, m_tr, m_1, m_2]:
            RuleApproval.objects.get_or_create(
                rule_version=rule_v1,
                membership=m,
                defaults={"decision": RuleApproval.Decision.APPROVED}
            )
            m.accepted_rules_version = rule_v1
            m.save()

        # Seed initial cycle period and obligations
        period1, _ = ContributionPeriod.objects.get_or_create(
            group=sample_group,
            period_number=1,
            defaults={
                "start_date": date.today(),
                "due_date": date.today() + timedelta(days=7),
                "status": ContributionPeriod.PeriodStatus.OPEN
            }
        )

        for m in [m_org, m_tr, m_1, m_2]:
            ContributionObligation.objects.get_or_create(
                group=sample_group,
                membership=m,
                period=period1,
                defaults={
                    "expected_amount": Decimal("2500.00"),
                    "currency": "ETB",
                    "due_date": date.today() + timedelta(days=7),
                    "status": ContributionObligation.ObligationStatus.PENDING
                }
            )

        self.stdout.write(self.style.SUCCESS("Successfully seeded initial Digital Equb data!"))
