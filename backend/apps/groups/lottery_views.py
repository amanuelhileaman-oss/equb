from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.groups.models import EqubGroup, GroupMembership, EqubCycle, LotteryRound, LotteryResult
from apps.groups.serializers import (
    EqubCycleSerializer,
    LotteryRoundSerializer,
    LotteryResultSerializer,
)
from apps.groups.lottery_services import (
    ensure_active_cycle,
    get_or_create_lottery_round,
    check_round_readiness,
    execute_lottery_for_round,
    start_next_cycle,
)


class OrganizerGroupLotteryView(APIView):
    """
    GET: Retrieves lottery details for an Equb group:
    - Active cycle information
    - Active round status & postponed reason
    - Previous winners in this cycle
    - Remaining eligible candidates
    - Predetermined order (if Method A)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(EqubGroup, id=group_id)
        if group.organizer_id != request.user.id and not request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        cycle = ensure_active_cycle(group)
        current_round = get_or_create_lottery_round(group)
        
        # Readiness
        is_ready = False
        pending_count = 0
        reasons = []
        if current_round:
            is_ready, pending_count, reasons = check_round_readiness(current_round)

        # Previous winners in current cycle
        results = LotteryResult.objects.filter(cycle=cycle).select_related(
            'winner_membership__user', 'lottery_round'
        ).order_by('round_number')

        results_data = LotteryResultSerializer(results, many=True).data

        # Candidates not yet won
        previous_winners_ids = set(results.values_list('winner_membership_id', flat=True))
        all_active_members = group.memberships.filter(
            status=GroupMembership.MembershipStatus.ACTIVE
        ).select_related('user')

        remaining_candidates = [
            {
                "id": str(m.id),
                "name": m.user.full_name or m.user.username,
                "email": m.user.email,
                "phone_number": getattr(m.user, 'phone_number', ''),
                "has_won": m.id in previous_winners_ids
            }
            for m in all_active_members
        ]

        return Response({
            "group": {
                "id": str(group.id),
                "name": group.name,
                "lottery_method": group.lottery_method,
                "lottery_method_display": group.get_lottery_method_display(),
                "is_lottery_locked": group.is_lottery_locked,
                "current_cycle_number": group.current_cycle_number,
                "contribution_amount": str(group.contribution_amount),
                "capacity": group.capacity,
                "grace_period_days": group.grace_period_days
            },
            "cycle": EqubCycleSerializer(cycle).data if cycle else None,
            "current_round": LotteryRoundSerializer(current_round).data if current_round else None,
            "readiness": {
                "is_ready": is_ready,
                "pending_unpaid_count": pending_count,
                "reasons": reasons
            },
            "winners_history": results_data,
            "candidates": remaining_candidates,
            "predetermined_order": cycle.completion_report.get('predetermined_order', []) if cycle else []
        })


class OrganizerTriggerLotteryDrawView(APIView):
    """
    POST: Triggers execution of the lottery draw for the current round.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(EqubGroup, id=group_id)
        # Super Admin must NOT intervene in individual group lottery decisions
        if group.organizer_id != request.user.id:
            return Response(
                {"error": "Unauthorized: Platform Super Admin cannot trigger individual group lotteries. Only the group organizer may execute draws."},
                status=status.HTTP_403_FORBIDDEN
            )

        current_round = get_or_create_lottery_round(group)
        if not current_round:
            return Response({"error": "No active lottery round available."}, status=status.HTTP_400_BAD_REQUEST)

        force = request.data.get('force', False)
        success, message, result = execute_lottery_for_round(
            current_round,
            triggered_by=request.user,
            force=force
        )

        if not success:
            return Response({"error": message, "round": LotteryRoundSerializer(current_round).data}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": message,
            "result": LotteryResultSerializer(result).data if result else None,
            "round": LotteryRoundSerializer(current_round).data
        }, status=status.HTTP_200_OK)


class OrganizerStartNextCycleView(APIView):
    """
    POST: Starts next cycle for the group once the previous cycle has concluded.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id):
        group = get_object_or_404(EqubGroup, id=group_id)
        # Super Admin must NOT intervene in individual group lottery decisions
        if group.organizer_id != request.user.id:
            return Response(
                {"error": "Unauthorized: Platform Super Admin cannot trigger individual group lotteries. Only the group organizer may execute draws."},
                status=status.HTTP_403_FORBIDDEN
            )

        new_cycle = start_next_cycle(group, authorized_by=request.user)
        return Response({
            "message": f"Cycle {new_cycle.cycle_number} started successfully.",
            "cycle": EqubCycleSerializer(new_cycle).data
        }, status=status.HTTP_201_CREATED)


class MemberGroupLotteryView(APIView):
    """
    GET: Member view of lottery schedule, method, previous winners, and cryptographic audit hash.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        group = get_object_or_404(EqubGroup, id=group_id)
        is_member = group.memberships.filter(user=request.user, status=GroupMembership.MembershipStatus.ACTIVE).exists()
        if not is_member and group.organizer_id != request.user.id and not request.user.is_staff:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        cycle = ensure_active_cycle(group)
        current_round = get_or_create_lottery_round(group)

        results = LotteryResult.objects.filter(cycle=cycle).select_related(
            'winner_membership__user', 'lottery_round'
        ).order_by('round_number')

        return Response({
            "group": {
                "id": str(group.id),
                "name": group.name,
                "lottery_method": group.lottery_method,
                "lottery_method_display": group.get_lottery_method_display(),
                "current_cycle_number": group.current_cycle_number,
                "contribution_amount": str(group.contribution_amount)
            },
            "cycle_number": cycle.cycle_number if cycle else 1,
            "current_round": LotteryRoundSerializer(current_round).data if current_round else None,
            "winners": LotteryResultSerializer(results, many=True).data
        })
