from decimal import Decimal
from datetime import date, timedelta
from django.db.models import Sum
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.subscriptions.models import SaasPlan, OrganizerSubscription
from apps.subscriptions.services import ensure_default_plans, get_or_create_active_subscription
from apps.groups.models import EqubGroup, GroupMembership, GroupInvitation
from apps.rules.models import RuleVersion, RuleApproval
from apps.contributions.models import ContributionPeriod, ContributionObligation
from apps.payments.models import GroupPaymentDestination, Payment, PaymentStatus, PaymentMethod
from apps.payouts.models import Payout, PayoutStatus, PayoutSettlementStatus, PayoutApproval
from apps.disputes.models import Dispute, DisputeStatus, DisputeCategory
from apps.audit_app.models import SupportTicket, Announcement, VerificationRecord

class Command(BaseCommand):
    help = "Seeds Selam Tesfaye organizer account and groups matching the reference mockup."

    def handle(self, *args, **options):
        self.stdout.write("1. Seeding base permissions and plans...")
        ensure_permissions_seeded()
        ensure_default_plans()

        growth_plan = SaasPlan.objects.filter(code='GROWTH_EQUB').first()
        if not growth_plan:
            growth_plan = SaasPlan.objects.create(
                code='GROWTH_EQUB',
                name='Growth Plan',
                description='Professional organizer plan for growing Equbs.',
                max_active_groups=5,
                price_etb=Decimal('600.00'),
                billing_cycle=SaasPlan.BillingCycle.MONTHLY,
                is_active=True
            )

        self.stdout.write("2. Creating/updating Selam Tesfaye organizer account...")
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
        selam.full_name = "Selam Tesfaye"
        selam.phone_number = "+251 911 123 456"
        selam.set_password("OrganizerPass123!")
        selam.save()

        # Update or set subscription
        sub = get_or_create_active_subscription(selam)
        sub.plan = growth_plan
        sub.status = OrganizerSubscription.SubscriptionStatus.ACTIVE
        sub.expires_at = timezone.now() + timezone.timedelta(days=30)
        sub.save()

        # Also ensure organizer@digitalequb.et has same plan for convenience
        dawit = User.objects.filter(email="organizer@digitalequb.et").first()
        if dawit:
            sub2 = get_or_create_active_subscription(dawit)
            sub2.plan = growth_plan
            sub2.expires_at = timezone.now() + timezone.timedelta(days=30)
            sub2.save()

        org_role = GroupRole.objects.get(group=None, code="GROUP_ORGANIZER")
        treasurer_role = GroupRole.objects.get(group=None, code="GROUP_TREASURER")
        member_role = GroupRole.objects.get(group=None, code="GROUP_MEMBER")

        # 3. Create Sample Member: Fitsum Abebe
        fitsum, _ = User.objects.get_or_create(
            email="fitsum.abebe@example.com",
            defaults={
                "full_name": "Fitsum Abebe",
                "phone_number": "+251 912 345 678",
                "is_email_verified": True,
                "account_status": User.AccountStatus.ACTIVE
            }
        )
        fitsum.set_password("MemberPass123!")
        fitsum.save()

        # 4. Group 1: Unity Equb Group (48 members, 5,000 ETB, Next: Jun 30, 2025)
        g1, _ = EqubGroup.objects.get_or_create(
            name="Unity Equb Group",
            defaults={
                "description": "Premier professional savings club in Addis Ababa.",
                "group_purpose": "Commercial Investment & Vehicle Purchase",
                "organizer": selam,
                "status": EqubGroup.GroupStatus.ACTIVE,
                "verification_status": EqubGroup.VerificationStatus.VERIFIED,
                "currency": "ETB",
                "contribution_amount": Decimal("5000.00"),
                "contribution_frequency": EqubGroup.Frequency.MONTHLY,
                "capacity": 50,
                "start_date": date(2025, 1, 1),
                "payout_method": EqubGroup.PayoutMethod.ROTATION_ORDER,
                "allowed_payment_methods": ["DIGITAL_PROVIDER", "CASH", "BANK_TRANSFER"],
                "rules_approval_threshold_percent": 100,
                "require_cash_second_confirmation": True
            }
        )
        g1.organizer = selam
        g1.save()

        # Add destination
        GroupPaymentDestination.objects.get_or_create(
            group=g1,
            provider_or_bank="Telebirr Merchant",
            defaults={
                "account_name": "Unity Equb Fund",
                "account_number": "0911002233",
                "is_verified": True,
                "is_active": True
            }
        )

        # Active rule v1
        rule_g1, _ = RuleVersion.objects.get_or_create(
            group=g1,
            version_number=1,
            defaults={
                "title": "Unity Equb Standard Charter v1",
                "terms_text": "Monthly contribution of 5,000 ETB due by month end. Payout by rotation order.",
                "contribution_amount": Decimal("5000.00"),
                "contribution_frequency": "MONTHLY",
                "status": RuleVersion.RuleStatus.APPROVED,
                "proposed_by": selam,
                "effective_at": timezone.now()
            }
        )
        g1.active_rules_version = rule_g1
        g1.save()

        # Period for Jun 30, 2025
        p1, _ = ContributionPeriod.objects.get_or_create(
            group=g1,
            period_number=6,
            defaults={
                "start_date": date(2025, 6, 1),
                "due_date": date(2025, 6, 30),
                "status": ContributionPeriod.PeriodStatus.OPEN
            }
        )

        # Memberships for G1: create organizer membership + Fitsum + seed up to 48 members
        m_selam1, _ = GroupMembership.objects.get_or_create(
            group=g1, user=selam,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 1, "joined_at": timezone.now(), "accepted_rules_version": rule_g1}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_selam1, role=org_role)

        m_fitsum, _ = GroupMembership.objects.get_or_create(
            group=g1, user=fitsum,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 2, "joined_at": timezone.now(), "accepted_rules_version": rule_g1}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_fitsum, role=member_role)

        # Create additional dummy members so count reaches 48
        current_g1_count = g1.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
        for i in range(current_g1_count + 1, 49):
            dummy_user, _ = User.objects.get_or_create(
                email=f"unity_member_{i}@digitalequb.et",
                defaults={"full_name": f"Member {i} Unity", "is_email_verified": True}
            )
            m_dummy, _ = GroupMembership.objects.get_or_create(
                group=g1, user=dummy_user,
                defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": i, "joined_at": timezone.now(), "accepted_rules_version": rule_g1}
            )
            MembershipRoleAssignment.objects.get_or_create(membership=m_dummy, role=member_role)

        # Assign Member 3 as Treasurer
        m_tr1 = g1.memberships.filter(payout_order_index=3).first()
        if m_tr1:
            MembershipRoleAssignment.objects.get_or_create(membership=m_tr1, role=treasurer_role)

        # Seed obligations for G1 totaling 140,000 ETB collected
        ob1, _ = ContributionObligation.objects.get_or_create(
            group=g1, membership=m_fitsum, period=p1,
            defaults={"expected_amount": Decimal("5000.00"), "amount_paid": Decimal("5000.00"), "due_date": date(2025, 6, 30), "status": ContributionObligation.ObligationStatus.PAID}
        )
        ob_selam, _ = ContributionObligation.objects.get_or_create(
            group=g1, membership=m_selam1, period=p1,
            defaults={"expected_amount": Decimal("140000.00"), "amount_paid": Decimal("140000.00"), "due_date": date(2025, 6, 30), "status": ContributionObligation.ObligationStatus.PAID}
        )

        # Payout scheduled for G1: 95,000 ETB for Jun 30, 2025
        Payout.objects.get_or_create(
            group=g1,
            recipient_membership=m_fitsum,
            amount=Decimal("95000.00"),
            defaults={
                "period": p1,
                "status": PayoutStatus.APPROVED,
                "settlement_status": PayoutSettlementStatus.AWAITING_SETTLEMENT,
                "requesting_user": selam,
                "notes": "Scheduled rotation payout for Jun 30, 2025"
            }
        )

        # 5. Group 2: Family Support Equb (35 members, 10,000 ETB, Next: Jul 05, 2025)
        g2, _ = EqubGroup.objects.get_or_create(
            name="Family Support Equb",
            defaults={
                "description": "Family and close community emergency & mutual support fund.",
                "group_purpose": "Family Resilience & Education Fees",
                "organizer": selam,
                "status": EqubGroup.GroupStatus.ACTIVE,
                "verification_status": EqubGroup.VerificationStatus.VERIFIED,
                "currency": "ETB",
                "contribution_amount": Decimal("10000.00"),
                "contribution_frequency": EqubGroup.Frequency.MONTHLY,
                "capacity": 40,
                "start_date": date(2025, 2, 1),
                "payout_method": EqubGroup.PayoutMethod.ROTATION_ORDER,
                "allowed_payment_methods": ["DIGITAL_PROVIDER", "BANK_TRANSFER"],
                "rules_approval_threshold_percent": 100
            }
        )
        g2.organizer = selam
        g2.save()

        rule_g2, _ = RuleVersion.objects.get_or_create(
            group=g2,
            version_number=1,
            defaults={
                "title": "Family Support Charter v1",
                "terms_text": "Monthly contribution of 10,000 ETB. Rotation order.",
                "contribution_amount": Decimal("10000.00"),
                "status": RuleVersion.RuleStatus.APPROVED,
                "proposed_by": selam
            }
        )
        g2.active_rules_version = rule_g2
        g2.save()

        p2, _ = ContributionPeriod.objects.get_or_create(
            group=g2, period_number=5,
            defaults={"start_date": date(2025, 6, 5), "due_date": date(2025, 7, 5), "status": ContributionPeriod.PeriodStatus.OPEN}
        )

        m_selam2, _ = GroupMembership.objects.get_or_create(
            group=g2, user=selam,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 1, "joined_at": timezone.now(), "accepted_rules_version": rule_g2}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_selam2, role=org_role)

        current_g2_count = g2.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
        for i in range(current_g2_count + 1, 36):
            dummy_user, _ = User.objects.get_or_create(
                email=f"family_member_{i}@digitalequb.et",
                defaults={"full_name": f"Family Member {i}", "is_email_verified": True}
            )
            m_dummy, _ = GroupMembership.objects.get_or_create(
                group=g2, user=dummy_user,
                defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": i, "joined_at": timezone.now(), "accepted_rules_version": rule_g2}
            )
            MembershipRoleAssignment.objects.get_or_create(membership=m_dummy, role=member_role)

        # Obligation for G2 totaling 95,000 ETB collected
        ContributionObligation.objects.get_or_create(
            group=g2, membership=m_selam2, period=p2,
            defaults={"expected_amount": Decimal("95000.00"), "amount_paid": Decimal("95000.00"), "due_date": date(2025, 7, 5), "status": ContributionObligation.ObligationStatus.PAID}
        )

        # 6. Group 3: Business Growth Equb (64 members, 7,000 ETB, Next: Jul 10, 2025)
        g3, _ = EqubGroup.objects.get_or_create(
            name="Business Growth Equb",
            defaults={
                "description": "Working capital equb for retail shop owners.",
                "group_purpose": "Inventory Procurement",
                "organizer": selam,
                "status": EqubGroup.GroupStatus.ACTIVE,
                "verification_status": EqubGroup.VerificationStatus.VERIFIED,
                "currency": "ETB",
                "contribution_amount": Decimal("7000.00"),
                "contribution_frequency": EqubGroup.Frequency.MONTHLY,
                "capacity": 70,
                "start_date": date(2025, 3, 1),
                "payout_method": EqubGroup.PayoutMethod.ROTATION_ORDER,
                "allowed_payment_methods": ["DIGITAL_PROVIDER", "CASH", "BANK_TRANSFER"]
            }
        )
        g3.organizer = selam
        g3.save()

        rule_g3, _ = RuleVersion.objects.get_or_create(
            group=g3, version_number=1,
            defaults={"title": "Business Growth Charter v1", "terms_text": "Monthly contribution 7,000 ETB.", "contribution_amount": Decimal("7000.00"), "status": RuleVersion.RuleStatus.APPROVED, "proposed_by": selam}
        )
        g3.active_rules_version = rule_g3
        g3.save()

        p3, _ = ContributionPeriod.objects.get_or_create(
            group=g3, period_number=4,
            defaults={"start_date": date(2025, 6, 10), "due_date": date(2025, 7, 10), "status": ContributionPeriod.PeriodStatus.OPEN}
        )

        m_selam3, _ = GroupMembership.objects.get_or_create(
            group=g3, user=selam,
            defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": 1, "joined_at": timezone.now(), "accepted_rules_version": rule_g3}
        )
        MembershipRoleAssignment.objects.get_or_create(membership=m_selam3, role=org_role)

        current_g3_count = g3.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
        for i in range(current_g3_count + 1, 65):
            dummy_user, _ = User.objects.get_or_create(
                email=f"biz_member_{i}@digitalequb.et",
                defaults={"full_name": f"Biz Member {i}", "is_email_verified": True}
            )
            m_dummy, _ = GroupMembership.objects.get_or_create(
                group=g3, user=dummy_user,
                defaults={"status": GroupMembership.MembershipStatus.ACTIVE, "payout_order_index": i, "joined_at": timezone.now(), "accepted_rules_version": rule_g3}
            )
            MembershipRoleAssignment.objects.get_or_create(membership=m_dummy, role=member_role)

        # Obligation for G3 totaling 50,000 ETB collected
        ContributionObligation.objects.get_or_create(
            group=g3, membership=m_selam3, period=p3,
            defaults={"expected_amount": Decimal("50000.00"), "amount_paid": Decimal("50000.00"), "due_date": date(2025, 7, 10), "status": ContributionObligation.ObligationStatus.PAID}
        )

        # 7. Seed Sample Dispute & Verification
        Dispute.objects.get_or_create(
            group=g1,
            reporter_membership=m_fitsum,
            title="Clarification on Bank Transfer Reconciliation",
            defaults={
                "category": DisputeCategory.PAYMENT_NOT_RECORDED,
                "description": "Sent bank transfer via CBE Mobile Banking. Awaiting second approval.",
                "status": DisputeStatus.OPEN
            }
        )

        VerificationRecord.objects.get_or_create(
            category=VerificationRecord.Category.ORGANIZER,
            target_id=str(selam.id),
            defaults={
                "target_name": selam.full_name,
                "status": VerificationRecord.Status.APPROVED,
                "submission_notes": "Kebele ID and Trade License verified by Super Admin."
            }
        )

        SupportTicket.objects.get_or_create(
            user=selam,
            subject="Question regarding CBE Birr bulk payout integration",
            defaults={
                "category": SupportTicket.Category.TECHNICAL,
                "message": "When will automated mobile wallet disbursements be enabled for CBE Birr accounts?",
                "status": SupportTicket.Status.OPEN
            }
        )

        self.stdout.write(self.style.SUCCESS(
            "Successfully seeded Selam Tesfaye organizer data!\n"
            f"Groups: {EqubGroup.objects.filter(organizer=selam).count()}\n"
            f"Total Members: {GroupMembership.objects.filter(group__organizer=selam, status='ACTIVE').count()}\n"
            f"Total Collected ETB: {ContributionObligation.objects.filter(group__organizer=selam).aggregate(s=Sum('amount_paid'))['s']}"
        ))
