import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership, GroupInvitation
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.contributions.models import ContributionPeriod, ContributionObligation
from apps.payments.models import (
    Payment, PaymentMethod, PaymentStatus, SettlementStatus,
    PaymentAllocation, GroupPaymentDestination
)
from apps.payouts.models import Payout, PayoutStatus, PayoutSettlementStatus
from apps.rules.models import RuleVersion
from apps.disputes.models import Dispute, DisputeCategory, DisputeStatus
from apps.notifications.models import Notification
from apps.audit_app.models import Announcement
from apps.ledger.services import record_contribution_ledger


class Command(BaseCommand):
    help = "Seeds real database data for Dawit Abebe (Member) matching the visual reference mockup"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("1. Seeding permissions and roles...")
        ensure_permissions_seeded()

        org_role = GroupRole.objects.get(group=None, code="GROUP_ORGANIZER")
        treasurer_role = GroupRole.objects.get(group=None, code="GROUP_TREASURER")
        member_role = GroupRole.objects.get(group=None, code="GROUP_MEMBER")

        # 1. Organizer: Selam Tesfaye
        selam, _ = User.objects.get_or_create(
            email="selam@example.com",
            defaults={
                "full_name": "Selam Tesfaye",
                "phone_number": "+251 911 123 456",
                "is_email_verified": True,
                "account_status": User.AccountStatus.ACTIVE,
                "preferred_language": "en"
            }
        )
        selam.set_password("OrganizerPass123!")
        selam.save()

        # 2. Treasurer: Abebe Kebede
        abebe, _ = User.objects.get_or_create(
            email="abebe@example.com",
            defaults={
                "full_name": "Abebe Kebede",
                "phone_number": "+251 911 234 567",
                "is_email_verified": True,
                "account_status": User.AccountStatus.ACTIVE,
                "preferred_language": "en"
            }
        )
        abebe.set_password("TreasurerPass123!")
        abebe.save()

        # 3. Member: Dawit Abebe
        self.stdout.write("2. Creating/updating Dawit Abebe member account...")
        dawit = User.objects.filter(email="dawit@example.com").first()
        if not dawit:
            # Check if another user has this phone number
            existing_phone = User.objects.filter(phone_number="+251 911 345 678").first()
            if existing_phone:
                dawit = existing_phone
                dawit.email = "dawit@example.com"
            else:
                dawit = User.objects.create(
                    email="dawit@example.com",
                    phone_number="+251 911 345 678",
                    is_email_verified=True,
                    account_status=User.AccountStatus.ACTIVE,
                    preferred_language="en"
                )
        dawit.full_name = "Dawit Abebe"
        dawit.set_password("MemberPass123!")
        dawit.save()

        # Also support alias login member@digitalequb.et
        dawit_alias = User.objects.filter(email="member@digitalequb.et").first()
        if not dawit_alias:
            dawit_alias = User.objects.create(
                email="member@digitalequb.et",
                phone_number="+251 911 999 888",
                is_email_verified=True,
                account_status=User.AccountStatus.ACTIVE,
                preferred_language="en"
            )
        dawit_alias.full_name = "Dawit Abebe"
        dawit_alias.set_password("MemberPass123!")
        dawit_alias.save()

        # 4. Group 1: Unity Business Equb
        unity_group, _ = EqubGroup.objects.get_or_create(
            name="Unity Business Equb",
            defaults={
                "organizer": selam,
                "status": EqubGroup.GroupStatus.ACTIVE,
                "verification_status": EqubGroup.VerificationStatus.VERIFIED,
                "currency": "ETB",
                "contribution_amount": Decimal("5000.00"),
                "contribution_frequency": EqubGroup.Frequency.MONTHLY,
                "capacity": 10,
                "start_date": date(2025, 1, 1),
                "payout_method": EqubGroup.PayoutMethod.ROTATION_ORDER,
                "group_purpose": "Commercial working capital and inventory bulk purchasing",
                "rules_approval_threshold_percent": 100
            }
        )

        # 5. Group 2: Family Support Equb
        family_group, _ = EqubGroup.objects.get_or_create(
            name="Family Support Equb",
            defaults={
                "organizer": selam,
                "status": EqubGroup.GroupStatus.ACTIVE,
                "verification_status": EqubGroup.VerificationStatus.VERIFIED,
                "currency": "ETB",
                "contribution_amount": Decimal("3000.00"),
                "contribution_frequency": EqubGroup.Frequency.MONTHLY,
                "capacity": 8,
                "start_date": date(2025, 2, 1),
                "payout_method": EqubGroup.PayoutMethod.ROTATION_ORDER,
                "group_purpose": "Family emergency reserves, home renovations, and school fees",
                "rules_approval_threshold_percent": 100
            }
        )

        # Ensure Active Rules
        rv1, _ = RuleVersion.objects.get_or_create(
            group=unity_group,
            version_number=1,
            defaults={
                "title": "Standard Commercial ROSCA Operating Agreement",
                "terms_text": "Monthly contribution of ETB 5,000 due by 30th of each calendar month.",
                "contribution_amount": Decimal("5000.00"),
                "contribution_frequency": "MONTHLY",
                "payout_method": "ROTATION_ORDER",
                "status": RuleVersion.RuleStatus.APPROVED,
                "proposed_by": selam,
                "effective_at": timezone.now() - timedelta(days=60)
            }
        )
        unity_group.active_rules_version = rv1
        unity_group.save()

        rv2, _ = RuleVersion.objects.get_or_create(
            group=family_group,
            version_number=1,
            defaults={
                "title": "Community Family Support Charter",
                "terms_text": "Monthly contribution of ETB 3,000 due by 5th of each calendar month.",
                "contribution_amount": Decimal("3000.00"),
                "contribution_frequency": "MONTHLY",
                "payout_method": "ROTATION_ORDER",
                "status": RuleVersion.RuleStatus.APPROVED,
                "proposed_by": selam,
                "effective_at": timezone.now() - timedelta(days=60)
            }
        )
        family_group.active_rules_version = rv2
        family_group.save()

        # Memberships for Dawit
        self.stdout.write("3. Enrolling Dawit into Unity Business and Family Support Equb...")
        m_unity, _ = GroupMembership.objects.get_or_create(
            group=unity_group,
            user=dawit,
            defaults={
                "status": GroupMembership.MembershipStatus.ACTIVE,
                "payout_order_index": 4,
                "joined_at": timezone.now() - timedelta(days=90),
                "accepted_rules_version": rv1
            }
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_unity, role=member_role)

        m_family, _ = GroupMembership.objects.get_or_create(
            group=family_group,
            user=dawit,
            defaults={
                "status": GroupMembership.MembershipStatus.ACTIVE,
                "payout_order_index": 2,
                "joined_at": timezone.now() - timedelta(days=60),
                "accepted_rules_version": rv2
            }
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_family, role=member_role)

        # Enroll for alias as well
        m_alias1, _ = GroupMembership.objects.get_or_create(
            group=unity_group,
            user=dawit_alias,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 5, "joined_at": timezone.now()}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_alias1, role=member_role)

        # Contribution Periods for Unity Business Equb
        p1_unity, _ = ContributionPeriod.objects.get_or_create(
            group=unity_group, period_number=1,
            defaults={"start_date": date(2025, 4, 1), "due_date": date(2025, 4, 30), "status": ContributionPeriod.PeriodStatus.SETTLED}
        )
        p2_unity, _ = ContributionPeriod.objects.get_or_create(
            group=unity_group, period_number=2,
            defaults={"start_date": date(2025, 5, 1), "due_date": date(2025, 5, 30), "status": ContributionPeriod.PeriodStatus.SETTLED}
        )
        p3_unity, _ = ContributionPeriod.objects.get_or_create(
            group=unity_group, period_number=3,
            defaults={"start_date": date(2025, 6, 1), "due_date": date(2025, 6, 30), "status": ContributionPeriod.PeriodStatus.OPEN}
        )

        # Periods for Family Support Equb
        p1_fam, _ = ContributionPeriod.objects.get_or_create(
            group=family_group, period_number=1,
            defaults={"start_date": date(2025, 5, 1), "due_date": date(2025, 5, 5), "status": ContributionPeriod.PeriodStatus.SETTLED}
        )
        p2_fam, _ = ContributionPeriod.objects.get_or_create(
            group=family_group, period_number=2,
            defaults={"start_date": date(2025, 6, 1), "due_date": date(2025, 6, 5), "status": ContributionPeriod.PeriodStatus.SETTLED}
        )
        p3_fam, _ = ContributionPeriod.objects.get_or_create(
            group=family_group, period_number=3,
            defaults={"start_date": date(2025, 7, 1), "due_date": date(2025, 7, 5), "status": ContributionPeriod.PeriodStatus.OPEN}
        )

        # Obligations for Dawit:
        # Unity Round 1: Paid ETB 5,000
        ob1_u, _ = ContributionObligation.objects.get_or_create(
            group=unity_group, membership=m_unity, period=p1_unity,
            defaults={"expected_amount": Decimal("5000.00"), "amount_paid": Decimal("5000.00"), "due_date": date(2025, 4, 30), "status": ContributionObligation.ObligationStatus.PAID}
        )
        # Unity Round 2: Paid ETB 5,000
        ob2_u, _ = ContributionObligation.objects.get_or_create(
            group=unity_group, membership=m_unity, period=p2_unity,
            defaults={"expected_amount": Decimal("5000.00"), "amount_paid": Decimal("5000.00"), "due_date": date(2025, 5, 30), "status": ContributionObligation.ObligationStatus.PAID}
        )
        # Unity Round 3: Pending ETB 5,000 (Due Jun 30, 2025)
        ob3_u, _ = ContributionObligation.objects.get_or_create(
            group=unity_group, membership=m_unity, period=p3_unity,
            defaults={"expected_amount": Decimal("5000.00"), "amount_paid": Decimal("0.00"), "due_date": date(2025, 6, 30), "status": ContributionObligation.ObligationStatus.PENDING}
        )

        # Confirmed Payments for Dawit: Total ETB 10,000
        self.stdout.write("4. Seeding confirmed payments and receipts for Dawit...")
        pay1, _ = Payment.objects.get_or_create(
            receipt_number="TXN-78452",
            defaults={
                "group": unity_group,
                "obligation": ob1_u,
                "payer": dawit,
                "payment_method": PaymentMethod.BANK_TRANSFER,
                "amount": Decimal("5000.00"),
                "status": PaymentStatus.CONFIRMED,
                "settlement_status": SettlementStatus.SETTLED,
                "transfer_reference": "CBE-ET-78452",
                "verified_by": abebe,
                "verified_at": timezone.now() - timedelta(days=35),
                "notes": "Bank transfer via CBE Mobile confirmed."
            }
        )
        pay2, _ = Payment.objects.get_or_create(
            receipt_number="TXN-78410",
            defaults={
                "group": unity_group,
                "obligation": ob2_u,
                "payer": dawit,
                "payment_method": PaymentMethod.DIGITAL_PROVIDER,
                "amount": Decimal("5000.00"),
                "status": PaymentStatus.CONFIRMED,
                "settlement_status": SettlementStatus.SETTLED,
                "provider_transaction_reference": "TELE-78410",
                "verified_by": abebe,
                "verified_at": timezone.now() - timedelta(days=5),
                "notes": "Telebirr direct payment checkout confirmed."
            }
        )

        # 5. Upcoming Payout for Dawit: ETB 15,000 in Family Support Equb
        self.stdout.write("5. Seeding upcoming payout of ETB 15,000 for Dawit...")
        payout_fam, _ = Payout.objects.get_or_create(
            group=family_group,
            period=p3_fam,
            recipient_membership=m_family,
            defaults={
                "amount": Decimal("15000.00"),
                "currency": "ETB",
                "status": PayoutStatus.APPROVED,
                "settlement_status": PayoutSettlementStatus.AWAITING_SETTLEMENT,
                "requesting_user": abebe,
                "notes": "Scheduled rotation disbursement for Dawit Abebe."
            }
        )

        # 6. Active Dispute #DS-2025-001
        self.stdout.write("6. Seeding active dispute #DS-2025-001...")
        disp, _ = Dispute.objects.get_or_create(
            group=unity_group,
            reporter_membership=m_unity,
            title="Dispute #DS-2025-001: Payment Not Recorded for Round 1 Bank Transfer",
            defaults={
                "category": DisputeCategory.PAYMENT_NOT_RECORDED,
                "description": "I submitted CBE reference CBE-ET-78452 two days ago, but receipt was initially delayed.",
                "status": DisputeStatus.UNDER_REVIEW,
                "assigned_handler": selam,
                "resolution_notes": "Organizer verified bank statement credit. Payment confirmed by Treasurer Abebe Kebede."
            }
        )

        # 7. Unread Notifications (3 count)
        self.stdout.write("7. Seeding 3 unread notifications...")
        Notification.objects.filter(user=dawit).delete()
        Notification.objects.create(
            user=dawit,
            group=unity_group,
            title="Contribution Due: Unity Business Equb",
            title_am="የአክሲዮን ክፍያ ማሳሰቢያ፡ ዩኒቲ ቢዝነስ እቁብ",
            message="Your Round 3 contribution of ETB 5,000 is due on Jun 30, 2025.",
            message_am="የዙር 3 እቁብ መዋጮ ብር 5,000 ሰኔ 30 ቀን 2025 ይጠበቃል።",
            notification_type=Notification.NotificationType.CONTRIBUTION_DUE,
            is_read=False
        )
        Notification.objects.create(
            user=dawit,
            group=family_group,
            title="Payout Scheduled: Family Support Equb",
            title_am="የእቁብ ድልድል ማስታወቂያ፡ ፋሚሊ ሰፖርት እቁብ",
            message="Congratulations! Your scheduled payout of ETB 15,000 is set for Jul 05, 2025.",
            message_am="እንኳን ደስ አለዎት! የብር 15,000 እቁብ ድልድልዎ ለሐምሌ 5 ቀን 2025 ተይዟል።",
            notification_type=Notification.NotificationType.PAYOUT_READY,
            is_read=False
        )
        Notification.objects.create(
            user=dawit,
            group=unity_group,
            title="Dispute Updated: #DS-2025-001",
            title_am="የአቤቱታ ማሻሻያ፡ #DS-2025-001",
            message="Organizer Selam Tesfaye added review notes to your dispute.",
            message_am="አስተባባሪ ሰላም ተስፋዬ ለአቤቱታዎ ማብራሪያ ጨምረዋል።",
            notification_type=Notification.NotificationType.GENERAL,
            is_read=False
        )

        # 8. Published Announcements
        self.stdout.write("8. Seeding published announcements...")
        Announcement.objects.get_or_create(
            title="Quarterly ROSCA Transparency Notice",
            defaults={
                "title_am": "የሩብ ዓመት የእቁብ ግልፅነት ማስታወቂያ",
                "content": "All group ledger reports and bank transfer audit reconciliations are verified for Q2.",
                "content_am": "ሁሉም የሂሳብ መዛግብት እና የባንክ ማመሳከሪያዎች ለ2ኛው ሩብ ዓመት ተረጋግጠዋል።",
                "target_audience": Announcement.TargetAudience.MEMBERS,
                "status": Announcement.Status.PUBLISHED,
                "published_at": timezone.now() - timedelta(days=2),
                "created_by": selam
            }
        )

        self.stdout.write(self.style.SUCCESS(
            "\n[SUCCESS] Seeded Member Mockup Data for Dawit Abebe:\n"
            "- Email: dawit@example.com (or member@digitalequb.et) / Password: MemberPass123!\n"
            "- Joined Groups: 2 (Unity Business Equb, Family Support Equb)\n"
            "- Confirmed Contributions: ETB 10,000\n"
            "- Outstanding Contributions: ETB 5,000 (Due Jun 30, 2025)\n"
            "- Upcoming Payout: ETB 15,000 (Scheduled Jul 05, 2025)\n"
            "- Unread Notifications: 3\n"
            "- Active Dispute: 1 (#DS-2025-001)\n"
        ))
