from rest_framework import serializers
from .models import Payment, PaymentAttempt, GroupPaymentDestination, PaymentAllocation
from apps.accounts.serializers import UserSerializer

class GroupPaymentDestinationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupPaymentDestination
        fields = [
            'id', 'group', 'provider_or_bank', 'account_name',
            'account_number', 'branch_or_details', 'transfer_instructions',
            'is_verified', 'is_active', 'created_at'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    payer_name = serializers.CharField(source='payer.full_name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    cash_receiver_name = serializers.CharField(source='cash_receiver.full_name', read_only=True)
    cash_confirmed_by_name = serializers.CharField(source='cash_confirmed_by.full_name', read_only=True)
    verified_by_name = serializers.CharField(source='verified_by.full_name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'receipt_number', 'group', 'group_name', 'obligation',
            'payer', 'payer_name', 'payment_method', 'amount', 'currency',
            'status', 'settlement_status', 'provider_transaction_reference',
            'transfer_reference', 'transfer_evidence_file',
            'cash_receiver', 'cash_receiver_name', 'cash_confirmed_by',
            'cash_confirmed_by_name', 'verified_by', 'verified_by_name',
            'verified_at', 'notes', 'created_at'
        ]


class CashReceiptCreateSerializer(serializers.Serializer):
    obligation_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    receipt_number = serializers.CharField(required=False, allow_blank=True, max_length=64)
    notes = serializers.CharField(required=False, allow_blank=True)


class BankTransferSubmitSerializer(serializers.Serializer):
    obligation_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    transfer_reference = serializers.CharField(max_length=120)
    notes = serializers.CharField(required=False, allow_blank=True)


class ReconciliationDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['CONFIRM', 'REJECT'])
    notes = serializers.CharField(required=False, allow_blank=True)
