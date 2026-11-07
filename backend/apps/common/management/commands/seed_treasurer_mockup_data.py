import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.contributions.models import ContributionPeriod, ContributionObligation
from apps.payments.models import (
    Payment, PaymentMethod, PaymentStatus, SettlementStatus,
    PaymentAllocation, ReconciliationException, GroupPaymentDestination
)
from apps.payouts.models import Payout, PayoutStatus, PayoutSettlementStatus
from apps.rules.models import RuleVersion
from apps.ledger.services import record_contribution_ledger, get_group_available_funds
from apps.notifications.models import Notification


class Command(BaseCommand):
    help = "Seeds real database data for Abebe Kebede (Treasurer) matching the visual reference mockup"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("1. Seeding permissions and roles...")
        ensure_permissions_seeded()

        # Group roles
        org_role = GroupRole.objects.get(group=None, code="GROUP_ORGANIZER")
        treasurer_role = GroupRole.objects.get(group=None, code="GROUP_TREASURER")
        member_role = GroupRole.objects.get(group=None, code="GROUP_MEMBER")

        # 2. Organizer: Selam Tesfaye
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

        # 3. Treasurer: Abebe Kebede
        self.stdout.write("2. Creating/updating Abebe Kebede treasurer account...")
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
        abebe.full_name = "Abebe Kebede"
        abebe.phone_number = "+251 911 234 567"
        abebe.set_password("TreasurerPass123!")
        abebe.save()

        # Also update treasurer@digitalequb.et to Abebe Kebede for convenient quick login
        tre_default = User.objects.filter(email="treasurer@digitalequb.et").first()
        if tre_default:
            tre_default.full_name = "Abebe Kebede"
            tre_default.set_password("TreasurerPass123!")
            tre_default.save()

        # 4. Mockup Members
        members_data = [
            ("Dawit Alemu", "dawit.alemu@example.com", "+251 911 345 671"),
            ("Hana Tamire", "hana.tamire@example.com", "+251 911 345 672"),
            ("Getachew Kebede", "getachew.k@example.com", "+251 911 345 673"),
            ("Fitsum Abebe", "fitsum.a@example.com", "+251 911 345 674"),
            ("Sara Mohammed", "sara.m@example.com", "+251 911 345 675"),
            ("Chala Bekele", "chala.b@example.com", "+251 911 345 676"),
            ("Almaz Ayana", "almaz.a@example.com", "+251 911 345 677"),
            ("Meron Getachew", "meron.g@example.com", "+251 911 345 678"),
            ("Tariku Bekele", "tariku.b@example.com", "+251 911 345 679"),
            ("Kibret Teshome", "kibret.t@example.com", "+251 911 345 680"),
        ]

        seeded_users = []
        for name, email, phone in members_data:
            u, _ = User.objects.get_or_create(
                email=email,
                defaults={"full_name": name, "phone_number": phone, "is_email_verified": True, "account_status": User.AccountStatus.ACTIVE}
            )
            u.full_name = name
            u.phone_number = phone
            u.set_password("MemberPass123!")
            u.save()
            seeded_users.append(u)

        # ==========================================================
        # GROUP 1: Unity Business Equb (10 members • ETB 5,000/month)
        # ==========================================================
        self.stdout.write("3. Seeding Group 1: Unity Business Equb...")
        g1, _ = EqubGroup.objects.get_or_create(
            name="Unity Business Equb",
            defaults={
                "description": "Monthly commercial Equb for Addis Ababa business owners.",
                "group_purpose": "Business Working Capital",
                "organizer": selam,
                "contribution_amount": Decimal("5000.00"),
                "contribution_frequency": "MONTHLY",
                "currency": "ETB",
                "status": EqubGroup.GroupStatus.ACTIVE,
                "verification_status": EqubGroup.VerificationStatus.VERIFIED,
                "start_date": date(2025, 1, 1),
                "require_cash_second_confirmation": True
            }
        )
        g1.contribution_amount = Decimal("5000.00")
        g1.status = EqubGroup.GroupStatus.ACTIVE
        g1.verification_status = EqubGroup.VerificationStatus.VERIFIED
        g1.require_cash_second_confirmation = True
        g1.save()

        # Destination
        GroupPaymentDestination.objects.get_or_create(
            group=g1,
            provider_or_bank="Telebirr Merchant",
            defaults={"account_name": "Unity Business Equb", "account_number": "0911223344", "is_verified": True, "is_active": True}
        )

        # Rule v1
        r1, _ = RuleVersion.objects.get_or_create(
            group=g1,
            version_number=1,
            defaults={
                "title": "Unity Business Charter v1",
                "terms_text": "Monthly contribution of ETB 5,000 due by 30th of each month.",
                "contribution_amount": Decimal("5000.00"),
                "contribution_frequency": "MONTHLY",
                "status": RuleVersion.RuleStatus.APPROVED,
                "proposed_by": selam,
                "effective_at": timezone.now()
            }
        )
        g1.active_rules_version = r1
        g1.save()

        # Periods (Rounds 1-6)
        p1, _ = ContributionPeriod.objects.get_or_create(
            group=g1, period_number=6,
            defaults={"start_date": date(2025, 6, 1), "due_date": date(2025, 6, 30), "status": ContributionPeriod.PeriodStatus.OPEN}
        )

        # Memberships for G1 (10 members)
        # Abebe (Treasurer)
        m_abebe1, _ = GroupMembership.objects.get_or_create(
            group=g1, user=abebe,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 1, "joined_at": timezone.now(), "accepted_rules_version": r1}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_abebe1, role=treasurer_role)

        # Selam (Organizer)
        m_selam1, _ = GroupMembership.objects.get_or_create(
            group=g1, user=selam,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 2, "joined_at": timezone.now(), "accepted_rules_version": r1}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_selam1, role=org_role)

        # Remaining 8 members to make 10 total
        g1_members = [m_abebe1, m_selam1]
        for idx, u in enumerate(seeded_users[:8], start=3):
            m, _ = GroupMembership.objects.get_or_create(
                group=g1, user=u,
                defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": idx, "joined_at": timezone.now(), "accepted_rules_version": r1}
            )
            MembershipRoleAssignment.objects.get_or_create(membership=m, role=member_role)
            g1_members.append(m)

        # Obligations for Period 6
        dawit_u = seeded_users[0] # Dawit Alemu
        hana_u = seeded_users[1]  # Hana Tamire
        getachew_u = seeded_users[2] # Getachew Kebede

        ob_dawit, _ = ContributionObligation.objects.get_or_create(
            group=g1, membership=g1_members[2], period=p1,
            defaults={"expected_amount": Decimal("5000.00"), "due_date": date(2025, 6, 30), "currency": "ETB", "status": ContributionObligation.ObligationStatus.PENDING}
        )
        ob_hana, _ = ContributionObligation.objects.get_or_create(
            group=g1, membership=g1_members[3], period=p1,
            defaults={"expected_amount": Decimal("5000.00"), "due_date": date(2025, 6, 30), "currency": "ETB", "status": ContributionObligation.ObligationStatus.PENDING}
        )
        ob_getachew, _ = ContributionObligation.objects.get_or_create(
            group=g1, membership=g1_members[4], period=p1,
            defaults={"expected_amount": Decimal("5000.00"), "due_date": date(2025, 6, 30), "currency": "ETB", "status": ContributionObligation.ObligationStatus.PENDING}
        )

        # Seed Mockup Recent Transactions:
        # Jun 28, 2025 | Dawit Alemu | ETB 5,000 | Confirmed | TXN-78452
        p_dawit, created = Payment.objects.get_or_create(
            receipt_number="RCP-TXN-78452",
            defaults={
                "group": g1, "obligation": ob_dawit, "payer": dawit_u,
                "payment_method": PaymentMethod.BANK_TRANSFER,
                "amount": Decimal("5000.00"), "currency": "ETB",
                "status": PaymentStatus.CONFIRMED,
                "settlement_status": SettlementStatus.SETTLED,
                "transfer_reference": "TXN-78452",
                "verified_by": abebe, "verified_at": timezone.now(),
                "notes": "Bank transfer verified via Telebirr merchant portal."
            }
        )
        if created:
            ob_dawit.amount_paid = Decimal("5000.00")
            ob_dawit.status = ContributionObligation.ObligationStatus.PAID
            ob_dawit.save()
            record_contribution_ledger(p_dawit, posted_by=abebe)

        # Jun 27, 2025 | Hana Tamire | ETB 5,000 | Confirmed | TXN-78451
        p_hana, created = Payment.objects.get_or_create(
            receipt_number="RCP-TXN-78451",
            defaults={
                "group": g1, "obligation": ob_hana, "payer": hana_u,
                "payment_method": PaymentMethod.CASH,
                "amount": Decimal("5000.00"), "currency": "ETB",
                "status": PaymentStatus.CONFIRMED,
                "settlement_status": SettlementStatus.NOT_APPLICABLE,
                "cash_receiver": abebe,
                "cash_confirmed_by": selam,
                "verified_by": selam, "verified_at": timezone.now(),
                "notes": "Cash received in-person and confirmed by organizer."
            }
        )
        if created:
            ob_hana.amount_paid = Decimal("5000.00")
            ob_hana.status = ContributionObligation.ObligationStatus.PAID
            ob_hana.save()
            record_contribution_ledger(p_hana, posted_by=selam)

        # Jun 26, 2025 | Getachew Kebede | ETB 5,000 | Pending | TXN-78450
        Payment.objects.get_or_create(
            receipt_number="RCP-TXN-78450",
            defaults={
                "group": g1, "obligation": ob_getachew, "payer": getachew_u,
                "payment_method": PaymentMethod.BANK_TRANSFER,
                "amount": Decimal("5000.00"), "currency": "ETB",
                "status": PaymentStatus.PENDING_VERIFICATION,
                "settlement_status": SettlementStatus.AWAITING_SETTLEMENT,
                "transfer_reference": "TXN-78450",
                "notes": "Awaiting bank statement reconciliation."
            }
        )

        # Seed additional confirmed contributions for previous periods so G1 totals ~120,000 ETB
        fitsum_u = seeded_users[3]
        for round_num in range(1, 5):
            p_hist, _ = ContributionPeriod.objects.get_or_create(
                group=g1, period_number=round_num,
                defaults={"start_date": date(2025, round_num, 1), "due_date": date(2025, round_num, 28), "status": ContributionPeriod.PeriodStatus.CLOSED}
            )
            # Create confirmed contribution
            ref = f"TXN-HIST-G1-{round_num}"
            if not Payment.objects.filter(receipt_number=f"RCP-{ref}").exists():
                pm = Payment.objects.create(
                    receipt_number=f"RCP-{ref}",
                    group=g1, payer=fitsum_u,
                    payment_method=PaymentMethod.DIGITAL_PROVIDER,
                    amount=Decimal("27500.00"), currency="ETB",
                    status=PaymentStatus.CONFIRMED,
                    settlement_status=SettlementStatus.SETTLED,
                    provider_transaction_reference=ref,
                    verified_at=timezone.now(),
                    notes=f"Round {round_num} bulk digital collections"
                )
                record_contribution_ledger(pm, posted_by=abebe)

        # ==========================================================
        # GROUP 2: Family Support Equb (8 members • ETB 3,000/month)
        # ==========================================================
        self.stdout.write("4. Seeding Group 2: Family Support Equb...")
        g2, _ = EqubGroup.objects.get_or_create(
            name="Family Support Equb",
            defaults={
                "description": "Community family and mutual emergency fund.",
                "group_purpose": "Family Savings & Education Support",
                "organizer": selam,
                "contribution_amount": Decimal("3000.00"),
                "contribution_frequency": "MONTHLY",
                "currency": "ETB",
                "status": EqubGroup.GroupStatus.ACTIVE,
                "verification_status": EqubGroup.VerificationStatus.VERIFIED,
                "start_date": date(2025, 1, 1),
                "require_cash_second_confirmation": True
            }
        )
        g2.contribution_amount = Decimal("3000.00")
        g2.status = EqubGroup.GroupStatus.ACTIVE
        g2.verification_status = EqubGroup.VerificationStatus.VERIFIED
        g2.require_cash_second_confirmation = True
        g2.save()

        # Memberships for G2: Abebe (Treasurer), Selam (Organizer), 6 members
        m_abebe2, _ = GroupMembership.objects.get_or_create(
            group=g2, user=abebe,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 1, "joined_at": timezone.now()}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_abebe2, role=treasurer_role)

        m_selam2, _ = GroupMembership.objects.get_or_create(
            group=g2, user=selam,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 2, "joined_at": timezone.now()}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_selam2, role=org_role)

        for idx, u in enumerate(seeded_users[4:10], start=3):
            m, _ = GroupMembership.objects.get_or_create(
                group=g2, user=u,
                defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": idx, "joined_at": timezone.now()}
            )
            MembershipRoleAssignment.objects.get_or_create(membership=m, role=member_role)

        # Seed confirmed contributions for G2 totaling ~65,000 ETB
        # Total across G1 (120,000) + G2 (65,000) = 185,000 ETB (matches mockup exactly!)
        if not Payment.objects.filter(receipt_number="RCP-TXN-G2-HIST").exists():
            pm2 = Payment.objects.create(
                receipt_number="RCP-TXN-G2-HIST",
                group=g2, payer=seeded_users[4],
                payment_method=PaymentMethod.BANK_TRANSFER,
                amount=Decimal("65000.00"), currency="ETB",
                status=PaymentStatus.CONFIRMED,
                settlement_status=SettlementStatus.SETTLED,
                transfer_reference="TXN-G2-HIST-01",
                verified_by=abebe, verified_at=timezone.now(),
                notes="Family Support Equb pooled confirmed collection"
            )
            record_contribution_ledger(pm2, posted_by=abebe)

        # ==========================================================
        # 3 PENDING APPROVALS (Matches Mockup: "Pending Approvals: 3")
        # ==========================================================
        self.stdout.write("5. Seeding 3 pending approvals...")
        # 1. Cash receipt recorded by Selam in G1 awaiting Abebe's confirmation
        ob_extra, _ = ContributionObligation.objects.get_or_create(
            group=g1, membership=g1_members[5], period=p1,
            defaults={"expected_amount": Decimal("5000.00"), "due_date": date(2025, 6, 30), "currency": "ETB", "status": ContributionObligation.ObligationStatus.PENDING}
        )
        Payment.objects.get_or_create(
            receipt_number="RCP-PEND-001",
            defaults={
                "group": g1, "obligation": ob_extra, "payer": seeded_users[3],
                "payment_method": PaymentMethod.CASH,
                "amount": Decimal("5000.00"), "currency": "ETB",
                "status": PaymentStatus.PENDING_VERIFICATION,
                "cash_receiver": selam, # Recorded by Selam so Abebe can independently approve!
                "notes": "Cash collected by Organizer at monthly assembly."
            }
        )

        # 2. Cash receipt recorded by Selam in G2 awaiting Abebe's confirmation
        Payment.objects.get_or_create(
            receipt_number="RCP-PEND-002",
            defaults={
                "group": g2, "payer": seeded_users[5],
                "payment_method": PaymentMethod.CASH,
                "amount": Decimal("3000.00"), "currency": "ETB",
                "status": PaymentStatus.PENDING_VERIFICATION,
                "cash_receiver": selam,
                "notes": "Cash delivered to group organizer."
            }
        )

        # 3. Upcoming Payout for Jun 30, 2025 awaiting approval (Matches Mockup: "Upcoming Payouts: 1 Next: Jun 30, 2025")
        payout_obj, _ = Payout.objects.get_or_create(
            group=g1, period=p1, recipient_membership=g1_members[2], # Dawit Alemu
            defaults={
                "amount": Decimal("50000.00"),
                "currency": "ETB",
                "status": PayoutStatus.PENDING_APPROVAL,
                "settlement_status": PayoutSettlementStatus.NOT_APPLICABLE,
                "requesting_user": selam,
                "notes": "Scheduled rotation payout for Round 6 due on Jun 30, 2025."
            }
        )
        payout_obj.status = PayoutStatus.PENDING_APPROVAL
        payout_obj.save()

        # Seed 1 Flagged Reconciliation Exception
        ReconciliationException.objects.get_or_create(
            reference_number="TXN-DUP-99120",
            group=g1,
            defaults={
                "flagged_by": abebe,
                "exception_type": ReconciliationException.ExceptionType.DUPLICATE_REFERENCE,
                "expected_amount": Decimal("5000.00"),
                "actual_amount": Decimal("5000.00"),
                "description": "Reference TXN-DUP-99120 was submitted twice by different members.",
                "status": ReconciliationException.Status.OPEN
            }
        )

        # Seed 3 In-App Notifications for Abebe (Matching Mockup bell badge: 3)
        Notification.objects.get_or_create(
            user=abebe,
            title="Cash Receipt Awaiting Verification",
            defaults={
                "message": "Selam Tesfaye recorded 5,000 ETB cash for Fitsum Abebe. Your independent confirmation is required.",
                "message_am": "ሰላም ተስፋዬ ለፍፁም አበበ የ5,000 ብር ጥሬ ገንዘብ አስመዝግባለች። የእርስዎ ማረጋገጫ ያስፈልጋል።",
                "notification_type": Notification.NotificationType.CASH_VERIFICATION_REQUEST,
                "link_url": "/treasurer/approvals/"
            }
        )
        Notification.objects.get_or_create(
            user=abebe,
            title="Upcoming Payout Scheduled",
            defaults={
                "message": "Round 6 payout of ETB 50,000 to Dawit Alemu is scheduled for Jun 30, 2025.",
                "message_am": "የዙር 6 የ50,000 ብር ክፍያ ለዳዊት አለሙ ሰኔ 23፣ 2017 ተይዟል።",
                "notification_type": Notification.NotificationType.PAYOUT_READY,
                "link_url": "/treasurer/payouts/"
            }
        )
        Notification.objects.get_or_create(
            user=abebe,
            title="New Bank Transfer Submitted",
            defaults={
                "message": "Getachew Kebede submitted transfer reference TXN-78450 for reconciliation.",
                "message_am": "ጌታቸው ከበደ የባንክ ማስተላለፊያ ቁጥር TXN-78450 ለማረጋገጥ አስገብቷል።",
                "notification_type": Notification.NotificationType.BANK_RECONCILIATION_REQUEST,
                "link_url": "/treasurer/reconciliation/"
            }
        )

        self.stdout.write(self.style.SUCCESS(
            "Successfully seeded Abebe Kebede Treasurer data!\n"
            "- Assigned Groups: 2 (Unity Business Equb, Family Support Equb)\n"
            "- Total Contributions: ETB 185,000\n"
            "- Pending Approvals: 3 (Requires Review)\n"
            "- Upcoming Payouts: 1 (Next: Jun 30, 2025)\n"
            "- Recent Transactions: TXN-78452 (Confirmed), TXN-78451 (Confirmed), TXN-78450 (Pending)"
        ))
