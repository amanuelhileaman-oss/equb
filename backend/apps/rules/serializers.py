from rest_framework import serializers
from .models import RuleVersion, RuleApproval
from apps.accounts.serializers import UserSerializer

class RuleApprovalSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='membership.user.full_name', read_only=True)

    class Meta:
        model = RuleApproval
        fields = ['id', 'member_name', 'decision', 'comment', 'decided_at']


class RuleVersionSerializer(serializers.ModelSerializer):
    proposed_by_name = serializers.CharField(source='proposed_by.full_name', read_only=True)
    approvals = RuleApprovalSerializer(many=True, read_only=True)
    approval_stats = serializers.SerializerMethodField()
    my_vote = serializers.SerializerMethodField()

    class Meta:
        model = RuleVersion
        fields = [
            'id', 'group', 'version_number', 'title', 'terms_text',
            'contribution_amount', 'contribution_frequency', 'payout_method',
            'payout_order_manifest', 'approval_threshold_percent', 'status',
            'proposed_by_name', 'proposed_at', 'effective_at', 'approvals',
            'approval_stats', 'my_vote'
        ]

    def get_approval_stats(self, obj):
        active_count = obj.group.memberships.filter(status='ACTIVE').count()
        approved_count = obj.approvals.filter(decision='APPROVED').count()
        pct = (approved_count / active_count * 100) if active_count > 0 else 0
        return {
            'total_active_members': active_count,
            'approved_votes': approved_count,
            'current_percent': round(pct, 1),
            'required_percent': obj.approval_threshold_percent
        }

    def get_my_vote(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        vote = obj.approvals.filter(membership__user=request.user).first()
        if not vote:
            return None
        return {'decision': vote.decision, 'decided_at': vote.decided_at}


class RuleProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RuleVersion
        fields = [
            'title', 'terms_text', 'contribution_amount',
            'contribution_frequency', 'payout_method', 'approval_threshold_percent'
        ]
