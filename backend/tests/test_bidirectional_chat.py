import uuid
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.notifications.models import ChatMessage


class BidirectionalChatTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Super Admin
        self.super_admin = User.objects.create_superuser(
            email='superadmin@equb.et',
            password='TestPassword123!',
            full_name='Super Admin'
        )

        # 2. Organizer
        self.organizer = User.objects.create_user(
            email='organizer@equb.et',
            password='TestPassword123!',
            full_name='Abebe Organizer'
        )

        # 3. Group
        self.group = EqubGroup.objects.create(
            name='Arada Equb',
            organizer=self.organizer,
            contribution_amount=1000,
            start_date=timezone.now().date(),
            status=EqubGroup.GroupStatus.ACTIVE
        )

        # 4. Member
        self.member = User.objects.create_user(
            email='member@equb.et',
            password='TestPassword123!',
            full_name='Chala Member'
        )
        self.member_membership = GroupMembership.objects.create(
            group=self.group,
            user=self.member,
            status=GroupMembership.MembershipStatus.ACTIVE
        )

        # 5. Treasurer
        self.treasurer = User.objects.create_user(
            email='treasurer@equb.et',
            password='TestPassword123!',
            full_name='Dawit Treasurer'
        )
        self.treasurer_membership = GroupMembership.objects.create(
            group=self.group,
            user=self.treasurer,
            status=GroupMembership.MembershipStatus.ACTIVE
        )
        treasurer_role, _ = GroupRole.objects.get_or_create(code='GROUP_TREASURER', defaults={'name': 'Group Treasurer'})
        MembershipRoleAssignment.objects.create(membership=self.treasurer_membership, role=treasurer_role)

    def test_super_admin_organizer_chat_allowed(self):
        # Super Admin sends message to Organizer
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.post('/api/v1/chat/messages/', {
            'recipient_id': str(self.organizer.id),
            'message': 'Hello Organizer, how is the group progressing?'
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ChatMessage.objects.count(), 1)

        # Organizer retrieves messages and replies
        self.client.force_authenticate(user=self.organizer)
        get_res = self.client.get(f'/api/v1/chat/messages/?recipient_id={self.super_admin.id}')
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(get_res.data['messages']), 1)

        # Organizer sends reply
        reply_res = self.client.post('/api/v1/chat/messages/', {
            'recipient_id': str(self.super_admin.id),
            'message': 'Hello Super Admin! Everything is going smoothly.'
        })
        self.assertEqual(reply_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ChatMessage.objects.count(), 2)

    def test_organizer_member_and_treasurer_chat_allowed(self):
        # Organizer sends message to Member
        self.client.force_authenticate(user=self.organizer)
        res = self.client.post('/api/v1/chat/messages/', {
            'recipient_id': str(self.member.id),
            'message': 'Welcome to Arada Equb!'
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Member sees messages and replies to Organizer
        self.client.force_authenticate(user=self.member)
        reply_res = self.client.post('/api/v1/chat/messages/', {
            'recipient_id': str(self.organizer.id),
            'message': 'Thank you Organizer!'
        })
        self.assertEqual(reply_res.status_code, status.HTTP_201_CREATED)

        # Treasurer chats with Organizer
        self.client.force_authenticate(user=self.treasurer)
        tre_res = self.client.post('/api/v1/chat/messages/', {
            'recipient_id': str(self.organizer.id),
            'message': 'Contributions reconciled.'
        })
        self.assertEqual(tre_res.status_code, status.HTTP_201_CREATED)

    def test_super_admin_cannot_chat_with_member_or_treasurer(self):
        # Super Admin attempts to message Member -> 403 Forbidden
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.post('/api/v1/chat/messages/', {
            'recipient_id': str(self.member.id),
            'message': 'Direct message from SA'
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Super Admin can only communicate directly with Organizers', res.data['error'])

        # Super Admin attempts to message Treasurer -> 403 Forbidden
        res_tre = self.client.post('/api/v1/chat/messages/', {
            'recipient_id': str(self.treasurer.id),
            'message': 'Direct message to Treasurer'
        })
        self.assertEqual(res_tre.status_code, status.HTTP_403_FORBIDDEN)

        # Member attempts to message Super Admin -> 403 Forbidden
        self.client.force_authenticate(user=self.member)
        res_mem = self.client.post('/api/v1/chat/messages/', {
            'recipient_id': str(self.super_admin.id),
            'message': 'Attempt to contact SA'
        })
        self.assertEqual(res_mem.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_cannot_chat_with_another_member(self):
        other_member = User.objects.create_user(
            email='other_member@equb.et',
            password='TestPassword123!',
            full_name='Other Member'
        )
        GroupMembership.objects.create(
            group=self.group,
            user=other_member,
            status=GroupMembership.MembershipStatus.ACTIVE
        )

        self.client.force_authenticate(user=self.member)
        res = self.client.post('/api/v1/chat/messages/', {
            'recipient_id': str(other_member.id),
            'message': 'Hey peer member'
        })
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_organizer_contacts_returns_grouped_dropdown_options(self):
        self.client.force_authenticate(user=self.organizer)
        res = self.client.get('/api/v1/chat/contacts/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        data = res.data
        self.assertEqual(data['current_user_role'], 'ORGANIZER')
        self.assertTrue(len(data['super_admins']) >= 1)
        self.assertEqual(data['super_admins'][0]['role'], 'SUPER_ADMIN')
        self.assertTrue(len(data['group_members']) >= 2)
        # Should contain member and treasurer
        roles = [m['role'] for m in data['group_members']]
        self.assertIn('MEMBER', roles)
        self.assertIn('TREASURER', roles)

    def test_member_contacts_only_contains_organizer(self):
        self.client.force_authenticate(user=self.member)
        res = self.client.get('/api/v1/chat/contacts/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        contacts = res.data['contacts']
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]['role'], 'ORGANIZER')
        self.assertEqual(contacts[0]['id'], str(self.organizer.id))
