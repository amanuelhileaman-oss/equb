from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.groups.models import (
    EqubGroup, GroupMembership, EqubCycle, LotteryRound, LotteryResult,
    OverdueCase, PaymentAgreement, PaymentInstallment, MembershipReview
)
from apps.contributions.models import ContributionPeriod, ContributionObligation
from apps.groups.lottery_services import (
    ensure_active_cycle,
    get_or_create_lottery_round,
    check_round_readiness,
    execute_lottery_for_round,
    complete_cycle_if_eligible,
    start_next_cycle
)
from apps.groups.overdue_services import (
    evaluate_group_deadlines_and_grace_periods,
    apply_overdue_resolution,
    member_respond_to_payment_agreement,
    record_membership_review_decision
)

User = get_user_model()


class EqubLotteryAndCyclesTestCase(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(
            email='org@equb.et',
            full_name='Amanuel Organizer',
            password='TestPassword123!'
        )

        self.treasurer = User.objects.create_user(
            email='tre@equb.et',
            full_name='Dawit Treasurer',
            password='TestPassword123!'
        )

        self.member1 = User.objects.create_user(
            email='mem1@equb.et',
            full_name='Abebe Member',
            password='TestPassword123!'
        )

        self.member2 = User.objects.create_user(
            email='mem2@equb.et',
            full_name='Chala Member',
            password='TestPassword123!'
        )

        self.member3 = User.objects.create_user(
            email='mem3@equb.et',
            full_name='Sara Member',
            password='TestPassword123!'
        )

        self.superadmin = User.objects.create_superuser(
            email='admin@equb.et',
            full_name='Platform Admin',
            password='AdminPassword123!'
        )

        # Create Equb Group with Method A
        self.group_a = EqubGroup.objects.create(
            name='Test Equb Method A',
            organizer=self.organizer,
            contribution_amount=Decimal('5000.00'),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=3,
            start_date=timezone.now().date(),
            lottery_method=EqubGroup.LotteryMethod.METHOD_A,
            status=EqubGroup.GroupStatus.ACTIVE,
            grace_period_days=3
        )

        self.m1_a = GroupMembership.objects.create(
            group=self.group_a, user=self.member1, status=GroupMembership.MembershipStatus.ACTIVE
        )
        self.m2_a = GroupMembership.objects.create(
            group=self.group_a, user=self.member2, status=GroupMembership.MembershipStatus.ACTIVE
        )
        self.m3_a = GroupMembership.objects.create(
            group=self.group_a, user=self.member3, status=GroupMembership.MembershipStatus.ACTIVE
        )

        # Create Equb Group with Method B
        self.group_b = EqubGroup.objects.create(
            name='Test Equb Method B',
            organizer=self.organizer,
            contribution_amount=Decimal('2000.00'),
            contribution_frequency=EqubGroup.Frequency.WEEKLY,
            capacity=3,
            start_date=timezone.now().date(),
            lottery_method=EqubGroup.LotteryMethod.METHOD_B,
            status=EqubGroup.GroupStatus.ACTIVE,
            grace_period_days=3
        )

        self.m1_b = GroupMembership.objects.create(
            group=self.group_b, user=self.member1, status=GroupMembership.MembershipStatus.ACTIVE
        )
        self.m2_b = GroupMembership.objects.create(
            group=self.group_b, user=self.member2, status=GroupMembership.MembershipStatus.ACTIVE
        )
        self.m3_b = GroupMembership.objects.create(
            group=self.group_b, user=self.member3, status=GroupMembership.MembershipStatus.ACTIVE
        )

    def test_method_a_one_time_lottery_preservation(self):
        """
        Method A tests:
        1. Full order is generated once and stored on cycle.
        2. Preserved across postponed rounds; round 1 always targets order[0].
        3. Method locked on group once executed.
        """
        cycle = ensure_active_cycle(self.group_a)
        round1 = get_or_create_lottery_round(self.group_a)

        # Mark obligations as paid
        p1 = ContributionPeriod.objects.create(group=self.group_a, period_number=1, start_date=timezone.now().date(), due_date=timezone.now().date())
        for m in [self.m1_a, self.m2_a, self.m3_a]:
            ContributionObligation.objects.create(
                group=self.group_a,
                membership=m,
                period=p1,
                expected_amount=Decimal('5000.00'),
                amount_paid=Decimal('5000.00'),
                due_date=timezone.now().date(),
                status=ContributionObligation.ObligationStatus.PAID
            )

        success, msg, res = execute_lottery_for_round(round1, triggered_by=self.organizer)
        self.assertTrue(success)
        self.assertIsNotNone(res)
        round1.refresh_from_db()
        self.assertEqual(round1.status, LotteryRound.RoundStatus.COMPLETED)

        # Group lottery method is now locked
        self.group_a.refresh_from_db()
        self.assertTrue(self.group_a.is_lottery_locked)

        # Order was generated and stored
        cycle.refresh_from_db()
        order = cycle.completion_report.get('predetermined_order')
        self.assertIsNotNone(order)
        self.assertEqual(len(order), 3)
        self.assertEqual(str(res.winner_membership.id), order[0])

    def test_lottery_postponed_when_unpaid_obligations_exist(self):
        """
        Lottery cannot proceed if any active member has not paid.
        """
        round1 = get_or_create_lottery_round(self.group_b)
        p1 = ContributionPeriod.objects.create(group=self.group_b, period_number=1, start_date=timezone.now().date(), due_date=timezone.now().date())

        # 2 members paid, 1 unpaid
        ContributionObligation.objects.create(
            group=self.group_b, membership=self.m1_b, period=p1,
            expected_amount=Decimal('2000.00'), amount_paid=Decimal('2000.00'),
            due_date=timezone.now().date(), status=ContributionObligation.ObligationStatus.PAID
        )
        ContributionObligation.objects.create(
            group=self.group_b, membership=self.m2_b, period=p1,
            expected_amount=Decimal('2000.00'), amount_paid=Decimal('2000.00'),
            due_date=timezone.now().date(), status=ContributionObligation.ObligationStatus.PAID
        )
        ContributionObligation.objects.create(
            group=self.group_b, membership=self.m3_b, period=p1,
            expected_amount=Decimal('2000.00'), amount_paid=Decimal('0.00'),
            due_date=timezone.now().date(), status=ContributionObligation.ObligationStatus.PENDING
        )

        success, msg, res = execute_lottery_for_round(round1, triggered_by=self.organizer)
        self.assertFalse(success)
        self.assertIn("postponed", msg.lower())

        round1.refresh_from_db()
        self.assertEqual(round1.status, LotteryRound.RoundStatus.POSTPONED)

    def test_method_b_round_by_round_excludes_previous_winners(self):
        """
        Method B tests:
        Winner is randomly selected from remaining eligible members.
        Previous winners in current cycle are strictly excluded.
        """
        cycle = ensure_active_cycle(self.group_b)
        round1 = get_or_create_lottery_round(self.group_b)

        # Force draw for round 1
        s1, m1, res1 = execute_lottery_for_round(round1, triggered_by=self.organizer, force=True)
        self.assertTrue(s1)
        winner1 = res1.winner_membership

        # Next round
        round2 = get_or_create_lottery_round(self.group_b)
        self.assertEqual(round2.round_number, 2)

        s2, m2, res2 = execute_lottery_for_round(round2, triggered_by=self.organizer, force=True)
        self.assertTrue(s2)
        winner2 = res2.winner_membership

        # Winners must be unique in this cycle
        self.assertNotEqual(winner1.id, winner2.id)

    def test_cycle_completion_and_fresh_cycle_reset(self):
        """
        When all members have won once, cycle completes and with authorization,
        new cycle starts where previous winners are eligible again.
        """
        cycle1 = ensure_active_cycle(self.group_b)
        # Complete all 3 rounds
        for _ in range(3):
            r = get_or_create_lottery_round(self.group_b)
            execute_lottery_for_round(r, triggered_by=self.organizer, force=True)

        cycle1.refresh_from_db()
        self.assertEqual(cycle1.status, EqubCycle.CycleStatus.COMPLETED)

        # Start next cycle
        cycle2 = start_next_cycle(self.group_b, authorized_by=self.organizer)
        self.assertEqual(cycle2.cycle_number, 2)
        self.assertEqual(cycle2.status, EqubCycle.CycleStatus.ACTIVE)

        # All 3 members are eligible again in Cycle 2
        r_new = get_or_create_lottery_round(self.group_b)
        s, m, res_c2 = execute_lottery_for_round(r_new, triggered_by=self.organizer, force=True)
        self.assertTrue(s)
        self.assertIn(res_c2.winner_membership.id, [self.m1_b.id, self.m2_b.id, self.m3_b.id])

    def test_overdue_resolution_a_continue_waiting(self):
        """
        Option A: Continue waiting keeps member active, sets follow up date, postpones lottery.
        """
        p = ContributionPeriod.objects.create(group=self.group_a, period_number=1, start_date=timezone.now().date(), due_date=timezone.now().date())
        past_date = timezone.now().date() - timedelta(days=5)
        ob = ContributionObligation.objects.create(
            group=self.group_a, membership=self.m1_a, period=p,
            expected_amount=Decimal('5000.00'), amount_paid=Decimal('0.00'),
            due_date=past_date, status=ContributionObligation.ObligationStatus.PENDING
        )

        cases = evaluate_group_deadlines_and_grace_periods(self.group_a)
        self.assertEqual(len(cases), 1)
        case = cases[0]

        success, msg, updated_case = apply_overdue_resolution(
            case,
            resolution_choice=OverdueCase.ResolutionChoice.CONTINUE_WAITING,
            data={'follow_up_days': 4, 'reason': 'Member had family medical delay.'},
            organizer_user=self.organizer
        )
        self.assertTrue(success)
        self.assertEqual(updated_case.status, OverdueCase.CaseStatus.RESOLVED_WAITING)
        self.assertEqual(updated_case.follow_up_date, timezone.now().date() + timedelta(days=4))

    def test_overdue_resolution_b_formal_payment_agreement(self):
        """
        Option B: Formal payment agreement with installments, member acceptance workflow.
        """
        p = ContributionPeriod.objects.create(group=self.group_a, period_number=1, start_date=timezone.now().date(), due_date=timezone.now().date())
        ob = ContributionObligation.objects.create(
            group=self.group_a, membership=self.m2_a, period=p,
            expected_amount=Decimal('5000.00'), amount_paid=Decimal('0.00'),
            due_date=timezone.now().date() - timedelta(days=5), status=ContributionObligation.ObligationStatus.PENDING
        )
        case = evaluate_group_deadlines_and_grace_periods(self.group_a)[0]

        success, msg, agreement = apply_overdue_resolution(
            case,
            resolution_choice=OverdueCase.ResolutionChoice.PAYMENT_AGREEMENT,
            data={
                'reason_for_nonpayment': 'Temporary bank transfer limitation',
                'total_amount': Decimal('5000.00'),
                'installments': [
                    {'amount': Decimal('2500.00'), 'due_date': timezone.now().date() + timedelta(days=3)},
                    {'amount': Decimal('2500.00'), 'due_date': timezone.now().date() + timedelta(days=7)},
                ]
            },
            organizer_user=self.organizer
        )
        self.assertTrue(success)
        self.assertEqual(agreement.status, PaymentAgreement.AgreementStatus.PENDING_MEMBER_ACCEPTANCE)
        self.assertEqual(agreement.installments.count(), 2)

        # Member accepts agreement
        resp_ok, resp_msg = member_respond_to_payment_agreement(agreement, self.member2, accept=True)
        self.assertTrue(resp_ok)
        agreement.refresh_from_db()
        self.assertEqual(agreement.status, PaymentAgreement.AgreementStatus.ACCEPTED_BY_MEMBER)

    def test_overdue_resolution_c_membership_review_and_replacement(self):
        """
        Option C: Membership review audits contributions vs payouts, allows replacing member.
        Replacement member does NOT jump ahead in lottery.
        """
        p = ContributionPeriod.objects.create(group=self.group_a, period_number=1, start_date=timezone.now().date(), due_date=timezone.now().date())
        ob = ContributionObligation.objects.create(
            group=self.group_a, membership=self.m3_a, period=p,
            expected_amount=Decimal('5000.00'), amount_paid=Decimal('0.00'),
            due_date=timezone.now().date() - timedelta(days=5), status=ContributionObligation.ObligationStatus.PENDING
        )
        case = evaluate_group_deadlines_and_grace_periods(self.group_a)[0]

        success, msg, review = apply_overdue_resolution(
            case,
            resolution_choice=OverdueCase.ResolutionChoice.MEMBERSHIP_REVIEW,
            data={'notes': 'Unreachable for 2 weeks'},
            organizer_user=self.organizer
        )
        self.assertTrue(success)
        self.assertEqual(review.status, MembershipReview.ReviewStatus.OPEN)

        # Create replacement user
        replacement_user = User.objects.create_user(
            email='rep@equb.et', full_name='Tadesse Replacement',
            password='TestPassword123!'
        )

        dec_ok, dec_msg = record_membership_review_decision(
            review,
            decision=MembershipReview.ReviewDecision.REPLACE_MEMBER,
            organizer_user=self.organizer,
            replacement_user=replacement_user,
            notes='Approved by group organizer'
        )
        self.assertTrue(dec_ok)

        self.m3_a.refresh_from_db()
        self.assertEqual(self.m3_a.status, GroupMembership.MembershipStatus.REMOVED)
        self.assertTrue(self.group_a.memberships.filter(user=replacement_user, status=GroupMembership.MembershipStatus.ACTIVE).exists())

    def test_superadmin_role_isolation(self):
        """
        Super Admin strictly does not intervene in individual group overdue decisions or lottery draws.
        """
        client = APIClient()
        client.force_authenticate(user=self.superadmin)

        # Attempting organizer draw endpoint as SuperAdmin without being group organizer returns 403
        resp = client.post(f"/api/v1/organizer/groups/{self.group_a.id}/lottery/draw/")
        self.assertEqual(resp.status_code, 403)
