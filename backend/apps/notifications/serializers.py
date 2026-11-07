from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'group', 'group_name', 'title', 'title_am',
            'message', 'message_am', 'notification_type',
            'is_read', 'link_url', 'created_at'
        ]
