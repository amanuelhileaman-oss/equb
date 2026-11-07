from django.utils import timezone
from rest_framework import views, permissions, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from .models import Dispute, DisputeEvidence
from .serializers import DisputeSerializer, DisputeCreateSerializer
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.services import has_group_permission
from apps.audit_app.services import log_audit_event

class DisputeListCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        group_id = request.query_params.get('group_id')
        if group_id:
            try:
                group = EqubGroup.objects.get(id=group_id)
            except (EqubGroup.DoesNotExist, ValueError):
                raise ValidationError("Group not found.")
            
            # Check permission: dispute managers or members
            if not user.is_platform_admin and not group.memberships.filter(user=user).exists():
                raise PermissionDenied("You do not belong to this group.")

            qs = Dispute.objects.filter(group=group)
            if not (user.is_platform_admin or has_group_permission(user, group, 'disputes:manage')):
                qs = qs.filter(reporter_membership__user=user)
        else:
            if user.is_platform_admin:
                qs = Dispute.objects.all()
            else:
                qs = Dispute.objects.filter(reporter_membership__user=user)

        serializer = DisputeSerializer(qs.select_related('group', 'reporter_membership__user').prefetch_related('evidence_attachments'), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DisputeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            group = EqubGroup.objects.get(id=data['group_id'])
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

        membership = group.memberships.filter(user=request.user, status=GroupMembership.MembershipStatus.ACTIVE).first()
        if not membership:
            raise PermissionDenied("Only active group members can submit disputes.")

        dispute = Dispute.objects.create(
            group=group,
            reporter_membership=membership,
            category=data['category'],
            title=data['title'],
            description=data['description']
        )

        evidence_file = request.FILES.get('evidence_file')
        if evidence_file:
            DisputeEvidence.objects.create(
                dispute=dispute,
                uploader=request.user,
                file=evidence_file,
                description=request.data.get('evidence_description', 'Dispute initial evidence')
            )

        log_audit_event(
            action="DISPUTE_SUBMITTED",
            actor=request.user,
            group=group,
            target_model="Dispute",
            target_id=dispute.id,
            details={"title": dispute.title, "category": dispute.category},
            request=request
        )

        return Response(DisputeSerializer(dispute).data, status=status.HTTP_201_CREATED)


class DisputeDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, dispute_id):
        try:
            dispute = Dispute.objects.get(id=dispute_id)
        except (Dispute.DoesNotExist, ValueError):
            raise ValidationError("Dispute not found.")

        group = dispute.group
        user = request.user
        if not (user.is_platform_admin or has_group_permission(user, group, 'disputes:manage')):
            raise PermissionDenied("You do not have permission to resolve or manage disputes in this group.")

        new_status = request.data.get('status')
        resolution_notes = request.data.get('resolution_notes')

        if new_status:
            dispute.status = new_status
            if new_status in ['RESOLVED', 'CLOSED']:
                dispute.resolved_at = timezone.now()
                dispute.assigned_handler = user

        if resolution_notes:
            dispute.resolution_notes = resolution_notes

        dispute.save()

        log_audit_event(
            action="DISPUTE_UPDATED",
            actor=user,
            group=group,
            target_model="Dispute",
            target_id=dispute.id,
            details={"status": dispute.status, "notes": resolution_notes},
            request=request
        )

        return Response(DisputeSerializer(dispute).data)
