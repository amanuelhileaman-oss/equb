from rest_framework import serializers
from .models import Payout, PayoutApproval

class PayoutApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source='approver.full_name', read_only=True)

    class Meta:
        model = PayoutApproval
        fields = ['id', 'approver', 'approver_name', 'decision', 'reason', 'decided_at']


class PayoutSerializer(serializers.ModelSerializer):
    recipient_name = serializers.CharField(source='recipient_membership.user.full_name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    requesting_user_name = serializers.CharField(source='requesting_user.full_name', read_only=True)
    executed_by_name = serializers.CharField(source='executed_by.full_name', read_only=True)
    approvals = PayoutApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = Payout
        fields = [
            'id', 'group', 'group_name', 'period', 'recipient_membership',
            'recipient_name', 'amount', 'currency', 'status', 'settlement_status',
            'requesting_user', 'requesting_user_name', 'requested_at',
            'executed_by', 'executed_by_name', 'executed_at', 'execution_reference',
            'settlement_evidence_file', 'blocking_reason', 'notes', 'approvals', 'created_at'
        ]


class PayoutRequestSerializer(serializers.Serializer):
    recipient_membership_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    period_id = serializers.UUIDField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class PayoutApprovalActionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['APPROVED', 'REJECTED'])
    reason = serializers.CharField(required=False, allow_blank=True)


class PayoutExecutionActionSerializer(serializers.Serializer):
    execution_reference = serializers.CharField(max_length=120)
    notes = serializers.CharField(required=False, allow_blank=True)
