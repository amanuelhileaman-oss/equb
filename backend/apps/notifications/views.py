from rest_framework import status, views, permissions
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer

class NotificationListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        serializer = NotificationSerializer(notifications, many=True)
        return Response({
            'unread_count': unread_count,
            'results': serializer.data
        })


class NotificationMarkReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save(update_fields=['is_read', 'updated_at'])
            return Response({'success': True, 'id': str(notification.id)})
        except Notification.DoesNotExist:
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


class NotificationMarkAllReadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'success': True, 'marked_read_count': updated})
