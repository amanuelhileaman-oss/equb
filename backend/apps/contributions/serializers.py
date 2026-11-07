from rest_framework import serializers
from .models import ContributionPeriod, ContributionObligation
from apps.groups.serializers import GroupMembershipSerializer

class ContributionPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContributionPeriod
        fields = ['id', 'group', 'period_number', 'start_date', 'due_date', 'status', 'created_at']


class ContributionObligationSerializer(serializers.ModelSerializer):
    membership = GroupMembershipSerializer(read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    period_number = serializers.IntegerField(source='period.period_number', read_only=True)
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = ContributionObligation
        fields = [
            'id', 'group', 'group_name', 'period', 'period_number',
            'membership', 'expected_amount', 'amount_paid', 'remaining_amount',
            'currency', 'due_date', 'status', 'created_at'
        ]
