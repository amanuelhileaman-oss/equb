from rest_framework import serializers
from .models import Notification, ChatMessage

class NotificationSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'group', 'group_name', 'title', 'title_am',
            'message', 'message_am', 'notification_type',
            'is_read', 'link_url', 'created_at'
        ]


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_email = serializers.CharField(source='sender.email', read_only=True)
    recipient_name = serializers.CharField(source='recipient.full_name', read_only=True)
    recipient_email = serializers.CharField(source='recipient.email', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'sender', 'sender_name', 'sender_email',
            'recipient', 'recipient_name', 'recipient_email',
            'group', 'group_name', 'message', 'is_read', 'created_at'
        ]

