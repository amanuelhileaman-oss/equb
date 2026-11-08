import uuid
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, views, permissions
from rest_framework.response import Response

from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership, TreasurerAssignmentRecord
from .models import ChatMessage, Notification
from .serializers import ChatMessageSerializer


def get_user_role(user):
    """Determine the primary role for chat authorization."""
    if user.is_platform_admin or user.is_superuser:
        return 'SUPER_ADMIN'
    
    if hasattr(user, 'organizer_profile') or EqubGroup.objects.filter(organizer=user).exists():
        return 'ORGANIZER'
    
    # Check if active treasurer in any group
    is_treasurer = GroupMembership.objects.filter(
        user=user,
        status=GroupMembership.MembershipStatus.ACTIVE,
        role_assignments__role__code='GROUP_TREASURER'
    ).exists() or TreasurerAssignmentRecord.objects.filter(user=user, is_active=True).exists()
    if is_treasurer:
        return 'TREASURER'
        
    return 'MEMBER'


def check_chat_permission(user_a, user_b):
    """
    Enforces strict chat boundaries:
    - Super Admin <-> Organizer (ALLOWED)
    - Organizer <-> Member / Treasurer (ALLOWED)
    - Super Admin <-> Member / Treasurer (STRICTLY FORBIDDEN)
    - Member <-> Member (FORBIDDEN)
    - Treasurer <-> Treasurer / Member (FORBIDDEN)
    """
    role_a = get_user_role(user_a)
    role_b = get_user_role(user_b)

    # 1. Super Admin <-> Organizer
    if (role_a == 'SUPER_ADMIN' and role_b == 'ORGANIZER') or (role_b == 'SUPER_ADMIN' and role_a == 'ORGANIZER'):
        return True, None

    # 2. Organizer <-> Member or Treasurer
    if (role_a == 'ORGANIZER' and role_b in ['MEMBER', 'TREASURER']) or (role_b == 'ORGANIZER' and role_a in ['MEMBER', 'TREASURER']):
        return True, None

    # 3. Super Admin <-> Member / Treasurer
    if (role_a == 'SUPER_ADMIN' and role_b in ['MEMBER', 'TREASURER']) or (role_b == 'SUPER_ADMIN' and role_a in ['MEMBER', 'TREASURER']):
        return False, "Super Admin can only communicate directly with Organizers. Direct chat with Members or Treasurers is not permitted."

    # 4. Member / Treasurer <-> Member / Treasurer
    if role_a in ['MEMBER', 'TREASURER'] and role_b in ['MEMBER', 'TREASURER']:
        return False, "Chat is only permitted between Members/Treasurers and their Group Organizer."

    return False, "Communication between these two accounts is not permitted."


class ChatContactsView(views.APIView):
    """
    Returns the allowed list of chat contacts based on the user's role.
    - Super Admin: List of all Organizers.
    - Organizer: Super Admin + all Members & Treasurers in their groups (grouped for dropdown selection).
    - Member / Treasurer: The Organizer(s) of their Equb group(s).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        role = get_user_role(user)
        contacts = []
        super_admins = []
        group_members = []

        if role == 'SUPER_ADMIN':
            # Contacts: All Organizers
            organizers = User.objects.filter(
                Q(organized_groups__isnull=False) | Q(organizer_profile__isnull=False)
            ).exclude(id=user.id).distinct()

            for org in organizers:
                unread = ChatMessage.objects.filter(sender=org, recipient=user, is_read=False).count()
                last_msg = ChatMessage.objects.filter(
                    Q(sender=user, recipient=org) | Q(sender=org, recipient=user)
                ).order_by('-created_at').first()

                groups_list = list(EqubGroup.objects.filter(organizer=org).values_list('name', flat=True)[:3])
                group_desc = ", ".join(groups_list) if groups_list else "Organizer"

                contacts.append({
                    'id': str(org.id),
                    'full_name': org.full_name,
                    'email': org.email,
                    'role': 'ORGANIZER',
                    'role_label': 'Group Organizer',
                    'group_name': group_desc,
                    'unread_count': unread,
                    'last_message': last_msg.message if last_msg else '',
                    'last_message_time': last_msg.created_at.isoformat() if last_msg else None,
                })

        elif role == 'ORGANIZER':
            # 1. Super Admin(s)
            sa_users = User.objects.filter(
                Q(is_platform_admin=True) | Q(is_superuser=True)
            ).filter(is_active=True).distinct()

            for sa in sa_users:
                unread = ChatMessage.objects.filter(sender=sa, recipient=user, is_read=False).count()
                last_msg = ChatMessage.objects.filter(
                    Q(sender=user, recipient=sa) | Q(sender=sa, recipient=user)
                ).order_by('-created_at').first()

                sa_contact = {
                    'id': str(sa.id),
                    'full_name': sa.full_name,
                    'email': sa.email,
                    'role': 'SUPER_ADMIN',
                    'role_label': 'Platform Super Admin',
                    'group_name': 'Platform Support & Administration',
                    'unread_count': unread,
                    'last_message': last_msg.message if last_msg else '',
                    'last_message_time': last_msg.created_at.isoformat() if last_msg else None,
                }
                super_admins.append(sa_contact)
                contacts.append(sa_contact)

            # 2. Members & Treasurers across organizer's groups
            org_groups = EqubGroup.objects.filter(organizer=user)
            memberships = GroupMembership.objects.filter(
                group__in=org_groups,
                status=GroupMembership.MembershipStatus.ACTIVE
            ).exclude(user=user).select_related('user', 'group').prefetch_related('role_assignments__role')

            seen_user_ids = set()
            for m in memberships:
                member_user = m.user
                is_tre = any(ra.role.code == 'GROUP_TREASURER' for ra in m.role_assignments.all()) or TreasurerAssignmentRecord.objects.filter(group=m.group, user=member_user, is_active=True).exists()
                role_label = 'Treasurer' if is_tre else 'Member'
                contact_role = 'TREASURER' if is_tre else 'MEMBER'

                unread = ChatMessage.objects.filter(sender=member_user, recipient=user, is_read=False).count()
                last_msg = ChatMessage.objects.filter(
                    Q(sender=user, recipient=member_user) | Q(sender=member_user, recipient=user)
                ).order_by('-created_at').first()

                member_contact = {
                    'id': str(member_user.id),
                    'full_name': member_user.full_name,
                    'email': member_user.email,
                    'role': contact_role,
                    'role_label': role_label,
                    'group_id': str(m.group.id),
                    'group_name': m.group.name,
                    'unread_count': unread,
                    'last_message': last_msg.message if last_msg else '',
                    'last_message_time': last_msg.created_at.isoformat() if last_msg else None,
                }
                group_members.append(member_contact)
                if member_user.id not in seen_user_ids:
                    seen_user_ids.add(member_user.id)
                    contacts.append(member_contact)

        else:
            # Role is MEMBER or TREASURER:
            # Contacts: ONLY their group Organizer(s). NO Super Admin!
            user_groups = EqubGroup.objects.filter(
                memberships__user=user,
                memberships__status=GroupMembership.MembershipStatus.ACTIVE
            ).select_related('organizer').distinct()

            seen_orgs = set()
            for g in user_groups:
                org = g.organizer
                if org.id not in seen_orgs:
                    seen_orgs.add(org.id)
                    unread = ChatMessage.objects.filter(sender=org, recipient=user, is_read=False).count()
                    last_msg = ChatMessage.objects.filter(
                        Q(sender=user, recipient=org) | Q(sender=org, recipient=user)
                    ).order_by('-created_at').first()

                    c = {
                        'id': str(org.id),
                        'full_name': org.full_name,
                        'email': org.email,
                        'role': 'ORGANIZER',
                        'role_label': 'Group Organizer',
                        'group_id': str(g.id),
                        'group_name': g.name,
                        'unread_count': unread,
                        'last_message': last_msg.message if last_msg else '',
                        'last_message_time': last_msg.created_at.isoformat() if last_msg else None,
                    }
                    contacts.append(c)

        total_unread = sum(c['unread_count'] for c in contacts)

        return Response({
            'current_user_role': role,
            'total_unread': total_unread,
            'contacts': contacts,
            'super_admins': super_admins,
            'group_members': group_members
        })


class ChatMessagesView(views.APIView):
    """
    Handles bidirectional message retrieval and sending.
    - GET ?recipient_id=<uuid>
    - POST { recipient_id, message, group_id? }
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        recipient_id = request.query_params.get('recipient_id')
        if not recipient_id:
            return Response({'error': 'recipient_id query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        recipient = get_object_or_404(User, id=recipient_id)

        # Enforce role boundary
        allowed, err_msg = check_chat_permission(request.user, recipient)
        if not allowed:
            return Response({'error': err_msg}, status=status.HTTP_403_FORBIDDEN)

        # Mark unread incoming messages from this recipient as read
        ChatMessage.objects.filter(
            sender=recipient,
            recipient=request.user,
            is_read=False
        ).update(is_read=True)

        messages = ChatMessage.objects.filter(
            (Q(sender=request.user, recipient=recipient) | Q(sender=recipient, recipient=request.user))
        ).order_by('created_at')

        serializer = ChatMessageSerializer(messages, many=True)
        return Response({
            'recipient': {
                'id': str(recipient.id),
                'full_name': recipient.full_name,
                'email': recipient.email,
                'role': get_user_role(recipient)
            },
            'messages': serializer.data
        })

    def post(self, request):
        recipient_id = request.data.get('recipient_id')
        message_text = request.data.get('message', '').strip()
        group_id = request.data.get('group_id')

        if not recipient_id:
            return Response({'error': 'recipient_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not message_text:
            return Response({'error': 'message content cannot be blank.'}, status=status.HTTP_400_BAD_REQUEST)

        recipient = get_object_or_404(User, id=recipient_id)

        # Enforce role boundary
        allowed, err_msg = check_chat_permission(request.user, recipient)
        if not allowed:
            return Response({'error': err_msg}, status=status.HTTP_403_FORBIDDEN)

        group = None
        if group_id:
            try:
                group = EqubGroup.objects.get(id=group_id)
            except (EqubGroup.DoesNotExist, ValueError):
                group = None

        chat_message = ChatMessage.objects.create(
            sender=request.user,
            recipient=recipient,
            group=group,
            message=message_text
        )

        serializer = ChatMessageSerializer(chat_message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
