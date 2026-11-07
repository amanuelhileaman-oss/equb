from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.groups.models import (
    EqubGroup,
    GroupMembership,
    TreasurerAssignmentRecord,
    OverdueCase,
    PaymentAgreement,
    PaymentInstallment,
    MembershipReview,
    LotteryRound,
)
from apps.contributions.models import ContributionObligation
from apps.notifications.models import Notification


def evaluate_group_deadlines_and_grace_periods(group):
    """
    Scans all pending/unpaid contribution obligations for the group:
    - Checks due date vs. grace_period_days.
    - Emits grace period reminders.
    - If grace period has expired, creates/updates an OverdueCase.
    - Automatically marks active lottery round as POSTPONED.
    """
    today = timezone.now().date()
    grace_days = group.grace_period_days or 3

    unpaid_obligations = ContributionObligation.objects.filter(
        group=group,
        membership__status=GroupMembership.MembershipStatus.ACTIVE,
        status__in=[ContributionObligation.ObligationStatus.PENDING, ContributionObligation.ObligationStatus.OVERDUE]
    ).select_related('membership__user', 'period')

    cases_created = []

    for ob in unpaid_obligations:
        due_date = ob.due_date
        if not due_date:
            continue

        if today > due_date:
            days_overdue = (today - due_date).days
            grace_expires_at = timezone.make_aware(
                timezone.datetime.combine(due_date + timedelta(days=grace_days), timezone.datetime.min.time())
            )
            unpaid_balance = ob.expected_amount - ob.amount_paid

            if days_overdue <= grace_days:
                Notification.objects.get_or_create(
                    user=ob.membership.user,
                    title=f"Payment Reminder: Grace Period Active ({days_overdue}/{grace_days} days)",
                    message=(
                        f"Your contribution of ETB {unpaid_balance:,.2f} for '{group.name}' is past due. "
                        f"You are currently in the {grace_days}-day grace period ({grace_days - days_overdue} day(s) remaining). "
                        "Please pay via Chapa to avoid formal overdue proceedings."
                    ),
                    notification_type=Notification.NotificationType.GRACE_PERIOD_STARTED,
                    defaults={'link_url': f"/contributions"}
                )
            else:
                case, created = OverdueCase.objects.get_or_create(
                    group=group,
                    membership=ob.membership,
                    obligation=ob,
                    defaults={
                        'period': ob.period,
                        'outstanding_amount': unpaid_balance,
                        'original_deadline': due_date,
                        'grace_period_days': grace_days,
                        'grace_period_expires_at': grace_expires_at,
                        'status': OverdueCase.CaseStatus.EXPIRED
                    }
                )
                if created:
                    cases_created.append(case)
                    if ob.status != ContributionObligation.ObligationStatus.OVERDUE:
                        ob.status = ContributionObligation.ObligationStatus.OVERDUE
                        ob.save(update_fields=['status'])

                    Notification.objects.create(
                        user=ob.membership.user,
                        title="Grace Period Expired: Contribution Overdue",
                        message=(
                            f"Your grace period for payment in '{group.name}' has expired. "
                            f"An overdue case has been opened. The lottery is postponed until resolved."
                        ),
                        notification_type=Notification.NotificationType.GRACE_PERIOD_EXPIRED,
                        link_url=f"/contributions"
                    )
                    if group.organizer:
                        Notification.objects.create(
                            user=group.organizer,
                            title=f"Overdue Case Opened: {ob.membership.user.full_name}",
                            message=(
                                f"Member {ob.membership.user.full_name} has an expired grace period "
                                f"for ETB {unpaid_balance:,.2f} in group '{group.name}'. Please choose a resolution option."
                            ),
                            notification_type=Notification.NotificationType.OVERDUE_CONTRIBUTION,
                            link_url=f"/groups/{group.id}/overdue"
                        )

    if unpaid_obligations.exists():
        postpone_active_lottery_rounds(group, reason="Pending or overdue contributions exist.")

    return cases_created


def postpone_active_lottery_rounds(group, reason="Overdue contributions"):
    """
    Postpones scheduled lottery rounds for this group.
    """
    from apps.groups.models import EqubCycle
    active_cycle = EqubCycle.objects.filter(group=group, status='ACTIVE').first()
    if active_cycle:
        rounds = LotteryRound.objects.filter(
            cycle=active_cycle,
            status=LotteryRound.RoundStatus.SCHEDULED
        )
        for r in rounds:
            r.status = LotteryRound.RoundStatus.POSTPONED
            r.postponed_reason = reason
            r.save(update_fields=['status', 'postponed_reason'])


def apply_overdue_resolution(overdue_case, resolution_choice, data, organizer_user):
    """
    Applies one of the 3 required resolution choices to an OverdueCase:
    - Choice A (CONTINUE_WAITING): Keeps member active, records organizer reason, follow-up date, notifies member/treasurer.
    - Choice B (PAYMENT_AGREEMENT): Proposes installment schedule with due dates & amounts.
    - Choice C (MEMBERSHIP_REVIEW): Initiates formal documented review, audits contributions vs. payouts, handles replacement.
    """
    with transaction.atomic():
        case = OverdueCase.objects.select_for_update().get(id=overdue_case.id)
        group = case.group
        membership = case.membership
        member_user = membership.user

        case.selected_resolution = resolution_choice
        case.resolution_reason = data.get('reason', data.get('notes', ''))
        case.resolved_by = organizer_user
        case.resolved_at = timezone.now()

        if resolution_choice == OverdueCase.ResolutionChoice.CONTINUE_WAITING:
            # OPTION A: CONTINUE WAITING
            follow_up_days = int(data.get('follow_up_days', 3))
            case.follow_up_date = timezone.now().date() + timedelta(days=follow_up_days)
            case.status = OverdueCase.CaseStatus.RESOLVED_WAITING
            case.history_log.append({
                "action": "CONTINUE_WAITING",
                "timestamp": timezone.now().isoformat(),
                "reason": case.resolution_reason,
                "follow_up_date": str(case.follow_up_date)
            })
            case.save()

            postpone_active_lottery_rounds(group, reason=f"Waiting for overdue member until {case.follow_up_date}.")

            Notification.objects.create(
                user=member_user,
                title="Extended Payment Notice: Continue Waiting",
                message=(
                    f"Organizer has noted: '{case.resolution_reason}'. "
                    f"You have been granted an extension until {case.follow_up_date} to complete your payment in '{group.name}'."
                ),
                notification_type=Notification.NotificationType.OVERDUE_CONTRIBUTION,
                link_url="/contributions"
            )

            treasurer_rec = TreasurerAssignmentRecord.objects.filter(group=group, is_active=True).first()
            if treasurer_rec:
                Notification.objects.create(
                    user=treasurer_rec.user,
                    title="Overdue Extension Notice",
                    message=(
                        f"Organizer chose 'Continue Waiting' for {member_user.full_name} "
                        f"in '{group.name}'. Follow-up scheduled for {case.follow_up_date}."
                    ),
                    notification_type=Notification.NotificationType.OVERDUE_CONTRIBUTION,
                    link_url=f"/treasurer"
                )

            return True, "Option A (Continue Waiting) applied successfully.", case

        elif resolution_choice == OverdueCase.ResolutionChoice.PAYMENT_AGREEMENT:
            # OPTION B: FORMAL PAYMENT AGREEMENT
            installments_data = data.get('installments', [])
            nonpayment_reason = data.get('reason_for_nonpayment', data.get('reason', 'Financial hardship / delay'))
            total_amount = Decimal(str(data.get('total_amount', case.outstanding_amount)))

            agreement = PaymentAgreement.objects.create(
                overdue_case=case,
                group=group,
                membership=membership,
                total_outstanding_amount=total_amount,
                remaining_balance=total_amount,
                member_reason=nonpayment_reason,
                status=PaymentAgreement.AgreementStatus.PENDING_MEMBER_ACCEPTANCE,
                created_by=organizer_user
            )

            for idx, inst in enumerate(installments_data):
                PaymentInstallment.objects.create(
                    agreement=agreement,
                    installment_number=idx + 1,
                    amount=Decimal(str(inst.get('amount'))),
                    due_date=inst.get('due_date'),
                    status=PaymentInstallment.InstallmentStatus.PENDING
                )

            case.status = OverdueCase.CaseStatus.RESOLVED_AGREEMENT
            case.history_log.append({
                "action": "PAYMENT_AGREEMENT_PROPOSED",
                "agreement_id": str(agreement.id),
                "timestamp": timezone.now().isoformat(),
                "total_amount": str(total_amount),
                "installments_count": len(installments_data)
            })
            case.save()

            Notification.objects.create(
                user=member_user,
                title="Formal Payment Agreement Proposed",
                message=(
                    f"A formal installment agreement for ETB {total_amount:,.2f} has been proposed for '{group.name}'. "
                    "Please review and accept the installment terms in your member portal."
                ),
                notification_type=Notification.NotificationType.PAYMENT_AGREEMENT_PROPOSED,
                link_url=f"/member/payment-agreements"
            )

            return True, "Option B (Payment Agreement) proposed with installment schedule.", agreement

        elif resolution_choice == OverdueCase.ResolutionChoice.MEMBERSHIP_REVIEW:
            # OPTION C: MEMBERSHIP REVIEW
            total_paid = Decimal('0.00')
            paid_obs = ContributionObligation.objects.filter(
                group=group,
                membership=membership,
                status=ContributionObligation.ObligationStatus.PAID
            )
            for ob in paid_obs:
                total_paid += ob.amount_paid

            from apps.groups.models import LotteryResult
            payouts_won = LotteryResult.objects.filter(
                winner_membership=membership
            )
            total_payouts = sum(
                Decimal(str(r.details.get('payout_amount', 0))) for r in payouts_won
            )
            net_obligation = total_paid - total_payouts

            review = MembershipReview.objects.create(
                overdue_case=case,
                group=group,
                membership=membership,
                status=MembershipReview.ReviewStatus.OPEN,
                documented_reason=data.get('notes', 'Initiated due to unresolved overdue contributions.'),
                initiated_by=organizer_user,
                previous_contributions_total=total_paid,
                previous_payouts_total=total_payouts,
                net_obligation_balance=net_obligation
            )

            case.status = OverdueCase.CaseStatus.RESOLVED_REVIEW
            case.history_log.append({
                "action": "MEMBERSHIP_REVIEW_INITIATED",
                "review_id": str(review.id),
                "timestamp": timezone.now().isoformat(),
                "net_obligation": str(net_obligation)
            })
            case.save()

            Notification.objects.create(
                user=member_user,
                title="Membership Review Initiated",
                message=(
                    f"A formal membership review has been initiated regarding your participation in '{group.name}'. "
                    f"Net financial status: Contributed ETB {total_paid:,.2f}, Received ETB {total_payouts:,.2f}."
                ),
                notification_type=Notification.NotificationType.MEMBERSHIP_REVIEW_INITIATED,
                link_url=f"/member/membership-reviews"
            )

            return True, "Option C (Membership Review) initiated with financial audit.", review

        return False, "Invalid resolution choice provided.", None


def member_respond_to_payment_agreement(agreement, member_user, accept=True, notes=''):
    """
    Handles member acceptance or rejection of a proposed payment agreement.
    """
    with transaction.atomic():
        agr = PaymentAgreement.objects.select_for_update().get(id=agreement.id)
        if agr.membership.user_id != member_user.id:
            return False, "Unauthorized: You are not the member associated with this agreement."

        if accept:
            agr.status = PaymentAgreement.AgreementStatus.ACCEPTED_BY_MEMBER
            agr.member_accepted_at = timezone.now()
            agr.save(update_fields=['status', 'member_accepted_at'])

            group = agr.group
            if group.organizer:
                Notification.objects.create(
                    user=group.organizer,
                    title="Payment Agreement Accepted by Member",
                    message=f"Member {member_user.full_name} has accepted the installment plan in '{group.name}'.",
                    notification_type=Notification.NotificationType.PAYMENT_AGREEMENT_APPROVED,
                    link_url=f"/groups/{group.id}/overdue"
                )
            return True, "Agreement accepted successfully."
        else:
            agr.status = PaymentAgreement.AgreementStatus.REJECTED_BY_MEMBER
            agr.member_rejection_reason = notes
            agr.save(update_fields=['status', 'member_rejection_reason'])

            group = agr.group
            if group.organizer:
                Notification.objects.create(
                    user=group.organizer,
                    title="Payment Agreement Rejected by Member",
                    message=f"Member {member_user.full_name} rejected the installment plan. Notes: {notes}",
                    notification_type=Notification.NotificationType.PAYMENT_AGREEMENT_PROPOSED,
                    link_url=f"/groups/{group.id}/overdue"
                )
            return True, "Agreement rejection recorded."


def record_membership_review_decision(review, decision, organizer_user, replacement_user=None, notes=''):
    """
    Records the final decision on a MembershipReview (Option C).
    Decisions:
    - REPLACE_MEMBER
    - REMOVE_MEMBER
    - REINSTATE_MEMBER
    """
    with transaction.atomic():
        rev = MembershipReview.objects.select_for_update().get(id=review.id)
        case = rev.overdue_case
        group = rev.group
        old_membership = rev.membership

        rev.decision = decision
        rev.decision_reason = notes
        rev.decision_date = timezone.now()
        rev.status = MembershipReview.ReviewStatus.DECIDED

        if decision == MembershipReview.ReviewDecision.REMOVE_MEMBER:
            old_membership.status = GroupMembership.MembershipStatus.REMOVED
            old_membership.save(update_fields=['status'])
            case.status = OverdueCase.CaseStatus.CLOSED_PAID
            case.save(update_fields=['status'])
            rev.save()

            Notification.objects.create(
                user=old_membership.user,
                title="Membership Terminated Following Review",
                message=f"Your membership in '{group.name}' has been terminated following group review.",
                notification_type=Notification.NotificationType.MEMBERSHIP_REVIEW_DECISION,
                link_url="/groups"
            )
            return True, "Member terminated from group."

        elif decision == MembershipReview.ReviewDecision.REPLACE_MEMBER and replacement_user:
            old_membership.status = GroupMembership.MembershipStatus.REMOVED
            old_membership.save(update_fields=['status'])

            new_membership = GroupMembership.objects.create(
                group=group,
                user=replacement_user,
                status=GroupMembership.MembershipStatus.ACTIVE
            )
            rev.replacement_user = replacement_user
            rev.save()

            from apps.groups.models import EqubCycle
            active_cycle = EqubCycle.objects.filter(group=group, status='ACTIVE').first()
            if active_cycle and active_cycle.completion_report.get('predetermined_order'):
                order = active_cycle.completion_report['predetermined_order']
                updated_order = [
                    str(new_membership.id) if m_id == str(old_membership.id) else m_id
                    for m_id in order
                ]
                active_cycle.completion_report['predetermined_order'] = updated_order
                active_cycle.save(update_fields=['completion_report'])

            case.status = OverdueCase.CaseStatus.CLOSED_PAID
            case.save(update_fields=['status'])

            Notification.objects.create(
                user=replacement_user,
                title=f"Welcome to {group.name}!",
                message=f"You have joined '{group.name}' as a replacement member.",
                notification_type=Notification.NotificationType.MEMBERSHIP_REVIEW_DECISION,
                link_url=f"/groups/{group.id}"
            )
            return True, f"Member replaced by {replacement_user.full_name or replacement_user.email}."

        rev.save()
        case.status = OverdueCase.CaseStatus.RESOLVED_WAITING
        case.save(update_fields=['status'])
        return True, "Review decision recorded."
