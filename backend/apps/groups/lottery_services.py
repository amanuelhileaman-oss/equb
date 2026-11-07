import hashlib
import json
import secrets
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.groups.models import (
    EqubGroup,
    GroupMembership,
    EqubCycle,
    LotteryRound,
    LotteryResult,
)
from apps.contributions.models import ContributionObligation
from apps.notifications.models import Notification


def ensure_active_cycle(group):
    """
    Ensures that an active EqubCycle exists for the given group.
    If none exists, initializes Cycle 1.
    """
    cycle = EqubCycle.objects.filter(group=group, status=EqubCycle.CycleStatus.ACTIVE).first()
    if not cycle:
        with transaction.atomic():
            cycle = EqubCycle.objects.select_for_update().filter(group=group, status=EqubCycle.CycleStatus.ACTIVE).first()
            if not cycle:
                last_cycle = EqubCycle.objects.filter(group=group).order_by('-cycle_number').first()
                cycle_num = (last_cycle.cycle_number + 1) if last_cycle else 1
                group.current_cycle_number = cycle_num
                group.save(update_fields=['current_cycle_number'])

                cycle = EqubCycle.objects.create(
                    group=group,
                    cycle_number=cycle_num,
                    lottery_method=group.lottery_method,
                    status=EqubCycle.CycleStatus.ACTIVE,
                    start_date=timezone.now().date()
                )
    return cycle


def get_or_create_lottery_round(group, period=None):
    """
    Returns the current active/scheduled lottery round for the group's active cycle.
    """
    cycle = ensure_active_cycle(group)

    with transaction.atomic():
        # Look for existing incomplete round
        round_obj = LotteryRound.objects.filter(
            cycle=cycle,
            status__in=[LotteryRound.RoundStatus.SCHEDULED, LotteryRound.RoundStatus.POSTPONED]
        ).order_by('round_number').first()

        if round_obj:
            return round_obj

        # Compute next round number
        completed_count = LotteryRound.objects.filter(cycle=cycle, status=LotteryRound.RoundStatus.COMPLETED).count()
        next_round_num = completed_count + 1

        active_members_count = group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
        if next_round_num > active_members_count and active_members_count > 0:
            complete_cycle_if_eligible(cycle)
            return None

        scheduled_time = timezone.now() + timezone.timedelta(hours=1)
        round_obj = LotteryRound.objects.create(
            group=group,
            cycle=cycle,
            period=period,
            round_number=next_round_num,
            lottery_method=group.lottery_method,
            status=LotteryRound.RoundStatus.SCHEDULED,
            scheduled_time=scheduled_time
        )
        return round_obj


def check_round_readiness(lottery_round):
    """
    Verifies that all active members in the group have paid their obligations for this round.
    Returns: (is_ready: bool, pending_count: int, reasons: list)
    """
    group = lottery_round.group
    active_memberships = group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE)

    pending_obligations = ContributionObligation.objects.filter(
        group=group,
        membership__in=active_memberships,
        status__in=[ContributionObligation.ObligationStatus.PENDING, ContributionObligation.ObligationStatus.OVERDUE]
    ).select_related('membership__user')

    if lottery_round.period:
        pending_obligations = pending_obligations.filter(period=lottery_round.period)

    reasons = []
    pending_count = pending_obligations.count()

    if pending_count > 0:
        names = [
            ob.membership.user.full_name or ob.membership.user.username
            for ob in pending_obligations[:5]
        ]
        reasons.append(
            f"{pending_count} active member(s) have unpaid contributions (e.g., {', '.join(names)})."
        )
        return False, pending_count, reasons

    return True, 0, []


def execute_lottery_for_round(lottery_round, triggered_by=None, force=False):
    """
    Executes the lottery draw for a specific LotteryRound.
    - Locks the lottery_method on group once executed.
    - Option A: One-time lottery order generation & preservation across postponed rounds.
    - Option B: Round-by-round selection from remaining eligible non-winners in current cycle.
    - Cryptographically secure selection using secrets.SystemRandom().
    - Verifiable SHA-256 audit hash.
    """
    with transaction.atomic():
        round_locked = LotteryRound.objects.select_for_update().get(id=lottery_round.id)
        cycle = EqubCycle.objects.select_for_update().get(id=round_locked.cycle_id)
        group = EqubGroup.objects.select_for_update().get(id=cycle.group_id)

        # Idempotency check: if already completed
        if round_locked.status == LotteryRound.RoundStatus.COMPLETED:
            existing_result = LotteryResult.objects.filter(lottery_round=round_locked).first()
            return True, "Lottery for this round was already executed.", existing_result

        # Check readiness unless explicitly forced by authorized organizer
        if not force:
            is_ready, pending_count, reasons = check_round_readiness(round_locked)
            if not is_ready:
                round_locked.status = LotteryRound.RoundStatus.POSTPONED
                reason_str = "; ".join(reasons)
                round_locked.postponed_reason = reason_str
                round_locked.save(update_fields=['status', 'postponed_reason'])

                # Notify members that lottery was postponed
                for mem in group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).select_related('user'):
                    Notification.objects.create(
                        user=mem.user,
                        title=f"Lottery Round {round_locked.round_number} Postponed",
                        message=f"The lottery for Round {round_locked.round_number} in '{group.name}' has been postponed. Reason: {reason_str}",
                        notification_type=Notification.NotificationType.LOTTERY_POSTPONED,
                        link_url=f"/groups/{group.id}/lottery"
                    )

                return False, f"Lottery postponed: {reason_str}", None

        # Lock lottery method configuration
        if not group.is_lottery_locked:
            group.is_lottery_locked = True
            group.save(update_fields=['is_lottery_locked'])

        active_memberships = list(group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).select_related('user').order_by('id'))
        if not active_memberships:
            return False, "Cannot execute lottery: No active members in this group.", None

        previous_winners_ids = set(
            LotteryResult.objects.filter(cycle=cycle).values_list('winner_membership_id', flat=True)
        )

        selected_winner = None
        eligible_candidates = []

        if group.lottery_method == EqubGroup.LotteryMethod.METHOD_A:
            # OPTION A: ONE-TIME LOTTERY ORDER
            # Check if cycle completion_report has predetermined order
            order = cycle.completion_report.get('predetermined_order')
            if not order:
                member_ids = [str(m.id) for m in active_memberships]
                rng = secrets.SystemRandom()
                rng.shuffle(member_ids)
                order = member_ids
                cycle.completion_report['predetermined_order'] = order
                cycle.save(update_fields=['completion_report'])

            round_idx = round_locked.round_number - 1
            if round_idx < len(order):
                target_id = order[round_idx]
                selected_winner = group.memberships.filter(id=target_id).first()

            if not selected_winner:
                fallback_pool = [m for m in active_memberships if m.id not in previous_winners_ids]
                selected_winner = secrets.SystemRandom().choice(fallback_pool) if fallback_pool else active_memberships[0]

            eligible_candidates = [
                {"id": str(m.id), "name": m.user.full_name or m.user.email}
                for m in active_memberships
            ]

        else:
            # OPTION B: ROUND-BY-ROUND LOTTERY
            remaining_pool = [m for m in active_memberships if m.id not in previous_winners_ids]
            if not remaining_pool:
                complete_cycle_if_eligible(cycle)
                return False, "All members have already won in this cycle.", None

            rng = secrets.SystemRandom()
            selected_winner = rng.choice(remaining_pool)
            eligible_candidates = [
                {"id": str(m.id), "name": m.user.full_name or m.user.email}
                for m in remaining_pool
            ]

        # Generate cryptographic audit hash
        timestamp_str = timezone.now().isoformat()
        salt = secrets.token_hex(16)
        raw_hash_input = (
            f"GROUP:{group.id}|CYCLE:{cycle.cycle_number}|ROUND:{round_locked.round_number}|"
            f"WINNER:{selected_winner.id}|SALT:{salt}|TIME:{timestamp_str}"
        )
        audit_hash = hashlib.sha256(raw_hash_input.encode('utf-8')).hexdigest()

        # Update round
        round_locked.status = LotteryRound.RoundStatus.COMPLETED
        round_locked.executed_at = timezone.now()
        round_locked.winner_membership = selected_winner
        round_locked.postponed_reason = ''
        round_locked.audit_hash = audit_hash
        round_locked.eligible_members_snapshot = eligible_candidates
        round_locked.audit_metadata = {
            "salt": salt,
            "timestamp": timestamp_str,
            "method_used": group.lottery_method,
            "triggered_by": triggered_by.email if triggered_by else "SYSTEM_AUTOMATION",
            "candidates_count": len(eligible_candidates)
        }
        round_locked.save()

        # Payout amount
        payout_amount = Decimal(str(group.contribution_amount)) * Decimal(str(len(active_memberships)))

        # Create LotteryResult
        lottery_result = LotteryResult.objects.create(
            cycle=cycle,
            lottery_round=round_locked,
            round_number=round_locked.round_number,
            winner_membership=selected_winner,
            draw_timestamp=round_locked.executed_at,
            lottery_method=group.lottery_method,
            verification_hash=audit_hash,
            details={
                "payout_amount": str(payout_amount),
                "salt": salt,
                "winner_name": selected_winner.user.full_name or selected_winner.user.email
            }
        )

        # Notify members
        winner_name = selected_winner.user.full_name or selected_winner.user.email
        for mem in active_memberships:
            is_winner = (mem.id == selected_winner.id)
            Notification.objects.create(
                user=mem.user,
                title="Congratulations! You Won the Equb Lottery!" if is_winner else f"Lottery Round {round_locked.round_number} Winner Announced",
                message=(
                    f"You have been selected as the winner for Round {round_locked.round_number} in '{group.name}'! Payout amount: ETB {payout_amount:,.2f}."
                    if is_winner else
                    f"Member {winner_name} has won the lottery for Round {round_locked.round_number} in '{group.name}' (ETB {payout_amount:,.2f})."
                ),
                notification_type=Notification.NotificationType.NEW_LOTTERY_WINNER if is_winner else Notification.NotificationType.LOTTERY_EXECUTED,
                link_url=f"/groups/{group.id}/lottery"
            )

        complete_cycle_if_eligible(cycle)

        return True, f"Lottery draw completed successfully for Round {round_locked.round_number}. Winner: {winner_name}", lottery_result


def complete_cycle_if_eligible(cycle):
    """
    Checks if all active members have won in the cycle.
    If so, transitions the cycle to COMPLETED.
    """
    group = cycle.group
    active_members_count = group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).count()
    completed_winners_count = LotteryResult.objects.filter(cycle=cycle).count()

    if completed_winners_count >= active_members_count and active_members_count > 0:
        if cycle.status != EqubCycle.CycleStatus.COMPLETED:
            cycle.status = EqubCycle.CycleStatus.COMPLETED
            cycle.completed_at = timezone.now()
            cycle.save(update_fields=['status', 'completed_at'])

            group.is_lottery_locked = False
            group.save(update_fields=['is_lottery_locked'])

            for mem in group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).select_related('user'):
                Notification.objects.create(
                    user=mem.user,
                    title=f"Cycle {cycle.cycle_number} Completed!",
                    message=f"Equb group '{group.name}' has successfully completed Cycle {cycle.cycle_number}! All {active_members_count} members have received their payouts.",
                    notification_type=Notification.NotificationType.NEW_CYCLE_CREATED,
                    link_url=f"/groups/{group.id}/lottery"
                )
            return True
    return False


def start_next_cycle(group, authorized_by):
    """
    Starts a fresh cycle for the Equb group.
    - All members become eligible again.
    - Increments group.current_cycle_number.
    """
    with transaction.atomic():
        active_cycle = EqubCycle.objects.filter(group=group, status=EqubCycle.CycleStatus.ACTIVE).first()
        if active_cycle:
            active_cycle.status = EqubCycle.CycleStatus.COMPLETED
            active_cycle.completed_at = timezone.now()
            active_cycle.save(update_fields=['status', 'completed_at'])

        new_cycle_number = group.current_cycle_number + 1
        group.current_cycle_number = new_cycle_number
        group.is_lottery_locked = False
        group.save(update_fields=['current_cycle_number', 'is_lottery_locked'])

        new_cycle = EqubCycle.objects.create(
            group=group,
            cycle_number=new_cycle_number,
            lottery_method=group.lottery_method,
            status=EqubCycle.CycleStatus.ACTIVE,
            start_date=timezone.now().date()
        )

        for mem in group.memberships.filter(status=GroupMembership.MembershipStatus.ACTIVE).select_related('user'):
            Notification.objects.create(
                user=mem.user,
                title=f"New Cycle {new_cycle_number} Started!",
                message=f"Organizer has initiated Cycle {new_cycle_number} for '{group.name}'. All members are eligible for the new lottery cycle.",
                notification_type=Notification.NotificationType.NEW_CYCLE_CREATED,
                link_url=f"/groups/{group.id}/lottery"
            )

        return new_cycle
