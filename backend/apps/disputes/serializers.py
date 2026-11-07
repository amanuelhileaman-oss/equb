from rest_framework import serializers
from .models import Dispute, DisputeEvidence

class DisputeEvidenceSerializer(serializers.ModelSerializer):
    uploader_name = serializers.CharField(source='uploader.full_name', read_only=True)

    class Meta:
        model = DisputeEvidence
        fields = ['id', 'uploader_name', 'file', 'description', 'uploaded_at']


class DisputeSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source='reporter_membership.user.full_name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    evidence_attachments = DisputeEvidenceSerializer(many=True, read_only=True)

    class Meta:
        model = Dispute
        fields = [
            'id', 'group', 'group_name', 'reporter_membership', 'reporter_name',
            'category', 'title', 'description', 'status', 'assigned_handler',
            'resolution_notes', 'resolved_at', 'evidence_attachments', 'created_at'
        ]


class DisputeCreateSerializer(serializers.Serializer):
    group_id = serializers.UUIDField()
    category = serializers.CharField(max_length=40)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
