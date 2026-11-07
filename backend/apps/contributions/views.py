from rest_framework import views, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import ContributionObligation, ContributionPeriod
from .serializers import ContributionObligationSerializer, ContributionPeriodSerializer
from apps.groups.models import EqubGroup
from apps.authorization.services import has_group_permission

class GroupObligationsListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, group_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

        # Check permissions: Treasurer, Organizer, or Member viewing their group obligations
        if not request.user.is_platform_admin and not group.memberships.filter(user=request.user).exists():
            raise PermissionDenied("You do not belong to this group.")

        qs = ContributionObligation.objects.filter(group=group).select_related(
            'group', 'period', 'membership__user'
        ).prefetch_related('membership__role_assignments__role')

        # Filter by status if requested
        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())

        # If ordinary member without financial role, filter to only their obligations
        if not (has_group_permission(request.user, group, 'contributions:view') and
                (has_group_permission(request.user, group, 'cash_payments:record') or
                 has_group_permission(request.user, group, 'group:manage')) or
                request.user.is_platform_admin):
            qs = qs.filter(membership__user=request.user)

        serializer = ContributionObligationSerializer(qs, many=True)
        return Response(serializer.data)


class MemberObligationsListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = ContributionObligation.objects.filter(
            membership__user=request.user
        ).select_related('group', 'period', 'membership__user').order_by('due_date')

        status_param = request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())

        serializer = ContributionObligationSerializer(qs, many=True)
        return Response(serializer.data)
