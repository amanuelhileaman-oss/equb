from rest_framework import serializers
from .models import (
    AuditLog, PlatformSetting, VerificationRecord,
    PaymentProviderConfiguration, Announcement, SecurityEvent, SupportTicket,
    SecurityIncident
)

class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.full_name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor', 'actor_name', 'group', 'group_name',
            'action', 'target_model', 'target_id', 'details',
            'ip_address', 'user_agent', 'timestamp'
        ]


class PlatformSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformSetting
        fields = ['key', 'value', 'description', 'updated_at']


class VerificationRecordSerializer(serializers.ModelSerializer):
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)

    class Meta:
        model = VerificationRecord
        fields = [
            'id', 'category', 'target_id', 'target_name', 'status',
            'submission_notes', 'decision_reason', 'documents',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'created_at', 'updated_at'
        ]


class PaymentProviderConfigurationSerializer(serializers.ModelSerializer):
    config_metadata = serializers.SerializerMethodField()

    class Meta:
        model = PaymentProviderConfiguration
        fields = [
            'id', 'provider_code', 'display_name', 'environment',
            'is_enabled', 'is_live_ready', 'connection_health',
            'failed_webhook_count', 'last_tested_at', 'last_webhook_at',
            'last_error_message', 'config_metadata', 'updated_at'
        ]

    def get_config_metadata(self, obj):
        meta = dict(obj.config_metadata or {})
        # Mask sensitive keys so secrets are never exposed
        for key in list(meta.keys()):
            if any(secret_term in key.lower() for secret_term in ['secret', 'key', 'password', 'token', 'cert', 'private']):
                val = str(meta[key])
                meta[key] = f"{val[:3]}...{val[-3:]}" if len(val) > 6 else "********"
        return meta


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    target_user_email = serializers.CharField(source='target_user.email', read_only=True)
    target_group_name = serializers.CharField(source='target_group.name', read_only=True)

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'title_am', 'content', 'content_am',
            'category', 'priority', 'channels',
            'target_audience', 'target_user', 'target_user_email',
            'target_group', 'target_group_name',
            'status', 'published_at',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]


class SecurityEventSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = SecurityEvent
        fields = [
            'id', 'event_type', 'severity', 'user', 'user_name', 'user_email',
            'ip_address', 'description', 'details', 'timestamp'
        ]

class SupportTicketSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'user', 'user_name', 'user_email', 'group', 'group_name',
            'category', 'subject', 'message', 'status', 'response_notes',
            'created_at', 'updated_at'
        ]


class SecurityIncidentSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)
    organizer_email = serializers.CharField(source='organizer.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.full_name', read_only=True)

    class Meta:
        model = SecurityIncident
        fields = [
            'id', 'incident_id', 'timestamp', 'organizer', 'organizer_email',
            'group', 'group_name', 'user', 'user_name', 'user_email',
            'user_group_role', 'attempted_operation', 'affected_resource',
            'risk_level', 'request_result', 'security_rule_triggered',
            'evidence_references', 'current_restrictions', 'status',
            'resolution_notes', 'resolved_by', 'resolved_by_name', 'resolved_at',
            'group_notified', 'group_notification_sent_at', 'group_notification_message'
        ]


