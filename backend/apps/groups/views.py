import uuid
from datetime import timedelta
from django.utils import timezone
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import EqubGroup, GroupMembership, GroupInvitation
from .serializers import EqubGroupSerializer, GroupCreateSerializer, GroupMembershipSerializer, GroupInvitationSerializer
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import has_group_permission
from apps.accounts.models import User
from apps.audit_app.services import log_audit_event

class GroupListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return GroupCreateSerializer
        return EqubGroupSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return EqubGroup.objects.all().select_related('organizer').prefetch_related('memberships')
        return EqubGroup.objects.filter(
            memberships__user=user
        ).distinct().select_related('organizer').prefetch_related('memberships')

    def perform_create(self, serializer):
        group = serializer.save()
        log_audit_event(
            action="GROUP_CREATED",
            actor=self.request.user,
            group=group,
            target_model="EqubGroup",
            target_id=group.id,
            request=self.request
        )


class GroupDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EqubGroupSerializer
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        if user.is_platform_admin:
            return EqubGroup.objects.all()
        return EqubGroup.objects.filter(memberships__user=user).distinct()

    def perform_update(self, serializer):
        group = self.get_object()
        if not has_group_permission(self.request.user, group, 'group:manage'):
            raise PermissionDenied("You do not have permission to manage this group's configuration.")
        updated_group = serializer.save()
        log_audit_event(
            action="GROUP_UPDATED",
            actor=self.request.user,
            group=updated_group,
            target_model="EqubGroup",
            target_id=updated_group.id,
            request=self.request
        )


class GroupMembersView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_group(self, group_id):
        try:
            return EqubGroup.objects.get(id=group_id)
        except (EqubGroup.DoesNotExist, ValueError):
            raise ValidationError("Group not found.")

    def get(self, request, group_id):
        group = self.get_group(group_id)
        # Check user is member or platform admin
        if not request.user.is_platform_admin and not group.memberships.filter(user=request.user).exists():
            raise PermissionDenied("You must belong to this group to view its members.")

        members = group.memberships.all().select_related('user').prefetch_related('role_assignments__role')
        return Response(GroupMembershipSerializer(members, many=True).data)

    def post(self, request, group_id):
        group = self.get_group(group_id)
        if not has_group_permission(request.user, group, 'group:manage_members'):
            raise PermissionDenied("You do not have permission to add members to this group.")

        email = request.data.get('email', '').strip().lower()
        if not email:
            raise ValidationError("Member email is required.")

        target_user = User.objects.filter(email=email).first()
        if target_user and group.memberships.filter(user=target_user).exists():
            raise ValidationError("This user is already a member of this Equb group.")

        token = uuid.uuid4().hex
        invitation = GroupInvitation.objects.create(
            group=group,
            invited_email=email,
            token=token,
            status=GroupInvitation.InvitationStatus.PENDING,
            expires_at=timezone.now() + timedelta(days=7)
        )

        # If user already registered, we can also create active membership directly if requested
        auto_activate = request.data.get('auto_activate', False)
        if target_user and auto_activate:
            membership = GroupMembership.objects.create(
                group=group,
                user=target_user,
                status=GroupMembership.MembershipStatus.ACTIVE,
                joined_at=timezone.now()
            )
            member_role, _ = GroupRole.objects.get_or_create(group=None, code="GROUP_MEMBER", defaults={"name": "Group Member", "is_system_role": True})
            MembershipRoleAssignment.objects.create(membership=membership, role=member_role, assigned_by=request.user)
            invitation.status = GroupInvitation.InvitationStatus.ACCEPTED
            invitation.save()
            log_audit_event(action="MEMBER_ADDED", actor=request.user, group=group, target_id=target_user.id, request=request)
            return Response(GroupMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

        log_audit_event(action="INVITATION_SENT", actor=request.user, group=group, details={"email": email}, request=request)
        return Response(GroupInvitationSerializer(invitation).data, status=status.HTTP_201_CREATED)


class AssignMemberRoleView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_id, membership_id):
        try:
            group = EqubGroup.objects.get(id=group_id)
            membership = GroupMembership.objects.get(id=membership_id, group=group)
        except (EqubGroup.DoesNotExist, GroupMembership.DoesNotExist, ValueError):
            raise ValidationError("Group or membership not found.")

        if not has_group_permission(request.user, group, 'group:manage_members'):
            raise PermissionDenied("You do not have permission to assign roles in this group.")

        role_code = request.data.get('role_code')
        if not role_code or role_code not in ['GROUP_ORGANIZER', 'GROUP_TREASURER', 'GROUP_MEMBER']:
            raise ValidationError("Invalid or unsupported role code.")

        role = GroupRole.objects.filter(code=role_code).first()
        if not role:
            raise ValidationError(f"Role {role_code} does not exist.")

        assignment, created = MembershipRoleAssignment.objects.get_or_create(
            membership=membership,
            role=role,
            defaults={'assigned_by': request.user}
        )
        log_audit_event(
            action="ROLE_ASSIGNED",
            actor=request.user,
            group=group,
            target_id=membership.id,
            details={"role": role_code, "user": membership.user.full_name},
            request=request
        )
        return Response({'success': True, 'message': f"Assigned role {role.name} to {membership.user.full_name}"})
