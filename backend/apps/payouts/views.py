from rest_framework import views, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import Payout
from .serializers import (
    PayoutSerializer, PayoutRequestSerializer,
    PayoutApprovalActionSerializer, PayoutExecutionActionSerializer
)
from .services import request_payout, approve_payout, execute_payout
from apps.groups.models import EqubGroup, GroupMembership
from apps.contributions.models import ContributionPeriod
from apps.audit_app.services import log_audit_event

class GroupPayoutsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

        if not request.user.is_platform_admin and not group.memberships.filter(user=request.user).exists():
            raise PermissionDenied("You do not belong to this group.")

        qs = Payout.objects.filter(group=group).select_related(
            'group', 'recipient_membership__user', 'requesting_user', 'executed_by'
        ).prefetch_related('approvals__approver').order_by('-created_at')

        serializer = PayoutSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

        serializer = PayoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            recipient = GroupMembership.objects.get(id=data['recipient_membership_id'], group=group)
        except GroupMembership.DoesNotExist:
            raise ValidationError("Recipient membership does not exist in this group.")

        period = None
        if data.get('period_id'):
            period = ContributionPeriod.objects.filter(id=data['period_id'], group=group).first()

        payout = request_payout(
            group=group,
            recipient_membership=recipient,
            requesting_user=request.user,
            amount=data.get('amount'),
            period=period,
            notes=data.get('notes', '')
        )

        log_audit_event(
            action="PAYOUT_REQUESTED",
            actor=request.user,
            group=group,
            target_model="Payout",
            target_id=payout.id,
            details={"recipient": recipient.user.full_name, "amount": str(payout.amount), "status": payout.status},
            request=request
        )

        return Response(PayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


class PayoutApprovalView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, payout_id):
        try:
            payout = Payout.objects.get(id=payout_id)
        except (Payout.DoesNotExist, ValueError):
            raise ValidationError("Payout not found.")

        serializer = PayoutApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data['decision']
        reason = serializer.validated_data.get('reason', '')

        approval = approve_payout(
            payout=payout,
            approver_user=request.user,
            decision=decision,
            reason=reason
        )

        log_audit_event(
            action=f"PAYOUT_DECISION_{decision}",
            actor=request.user,
            group=payout.group,
            target_model="Payout",
            target_id=payout.id,
            details={"decision": decision, "reason": reason},
            request=request
        )

        return Response(PayoutSerializer(payout).data)


class PayoutExecutionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, payout_id):
        try:
            payout = Payout.objects.get(id=payout_id)
        except (Payout.DoesNotExist, ValueError):
            raise ValidationError("Payout not found.")

        serializer = PayoutExecutionActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        evidence_file = request.FILES.get('evidence_file')

        executed = execute_payout(
            payout=payout,
            executor_user=request.user,
            execution_reference=data['execution_reference'],
            evidence_file=evidence_file,
            notes=data.get('notes', '')
        )

        log_audit_event(
            action="PAYOUT_EXECUTED",
            actor=request.user,
            group=payout.group,
            target_model="Payout",
            target_id=payout.id,
            details={"execution_reference": executed.execution_reference, "amount": str(executed.amount)},
            request=request
        )

        return Response(PayoutSerializer(executed).data)


class MemberPayoutsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Payout.objects.filter(
            recipient_membership__user=request.user
        ).select_related('group', 'recipient_membership__user', 'requesting_user').order_by('-created_at')

        serializer = PayoutSerializer(qs, many=True)
        return Response(serializer.data)
