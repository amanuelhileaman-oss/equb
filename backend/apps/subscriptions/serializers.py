from rest_framework import serializers
from .models import SaasPlan, OrganizerSubscription, SubscriptionInvoice

class SaasPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SaasPlan
        fields = [
            'id', 'code', 'name', 'description', 'max_active_groups',
            'price_etb', 'billing_cycle', 'is_active', 'created_at'
        ]


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionInvoice
        fields = [
            'id', 'invoice_number', 'amount_etb', 'due_date',
            'status', 'paid_at', 'payment_reference', 'created_at'
        ]


class OrganizerSubscriptionSerializer(serializers.ModelSerializer):
    plan = SaasPlanSerializer(read_only=True)
    invoices = SubscriptionInvoiceSerializer(many=True, read_only=True)

    class Meta:
        model = OrganizerSubscription
        fields = [
            'id', 'plan', 'status', 'started_at', 'expires_at',
            'auto_renew', 'invoices'
        ]
