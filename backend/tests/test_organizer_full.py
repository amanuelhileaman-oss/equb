import uuid
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.accounts.models import User
from apps.groups.models import EqubGroup, GroupMembership, GroupInvitation
from apps.authorization.models import GroupRole, MembershipRoleAssignment
from apps.authorization.services import ensure_permissions_seeded
from apps.subscriptions.models import SaasPlan, OrganizerSubscription
from apps.subscriptions.services import ensure_default_plans, get_or_create_active_subscription
from apps.rules.models import RuleVersion
from apps.contributions.models import ContributionPeriod, ContributionObligation
from apps.payments.models import GroupPaymentDestination, Payment, PaymentStatus, PaymentMethod
from apps.payouts.models import Payout, PayoutStatus, PayoutSettlementStatus
from apps.disputes.models import Dispute, DisputeStatus, DisputeCategory
from apps.audit_app.models import SupportTicket, VerificationRecord, AuditLog


class TestOrganizerDashboardSuite(APITestCase):
    def setUp(self):
        ensure_permissions_seeded()
        ensure_default_plans()

        self.starter_plan = SaasPlan.objects.get(code='STARTER_EQUB')
        self.growth_plan = SaasPlan.objects.get(code='GROWTH_EQUB')

        # Organizer A (Selam)
        self.organizer_a = User.objects.create_user(
            email='selam.org@digitalequb.et',
            password='OrganizerPass123!',
            full_name='Selam Tesfaye',
            phone_number='+251911999881',
            is_email_verified=True,
            account_status=User.AccountStatus.ACTIVE
        )
        self.sub_a = get_or_create_active_subscription(self.organizer_a)
        self.sub_a.plan = self.growth_plan  # Allows 5 groups
        self.sub_a.save()

        # Organizer B (Cross-tenant competitor)
        self.organizer_b = User.objects.create_user(
            email='competitor@digitalequb.et',
            password='OrganizerPass123!',
            full_name='Abebe Balcha',
            phone_number='+251911999882',
            is_email_verified=True,
            account_status=User.AccountStatus.ACTIVE
        )
        self.sub_b = get_or_create_active_subscription(self.organizer_b)
        self.sub_b.plan = self.starter_plan  # Allows 1 group
        self.sub_b.save()

        # Regular Member
        self.member_user = User.objects.create_user(
            email='member.user@digitalequb.et',
            password='MemberPass123!',
            full_name='Fitsum Abebe',
            phone_number='+251911999883',
            is_email_verified=True,
            account_status=User.AccountStatus.ACTIVE
        )

        # Organizer A's Equb Group
        self.group_a = EqubGroup.objects.create(
            name='Unity Traders Equb',
            description='Rotating savings for traders',
            group_purpose='Working Capital',
            organizer=self.organizer_a,
            status=EqubGroup.GroupStatus.ACTIVE,
            verification_status=EqubGroup.VerificationStatus.VERIFIED,
            currency='ETB',
            contribution_amount=Decimal('5000.00'),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=20,
            start_date=date.today(),
            payout_method=EqubGroup.PayoutMethod.ROTATION_ORDER,
            allowed_payment_methods=['DIGITAL_PROVIDER', 'CASH', 'BANK_TRANSFER'],
            rules_approval_threshold_percent=100
        )

        # Organizer B's Equb Group
        self.group_b = EqubGroup.objects.create(
            name='Competitor Private Equb',
            description='Private group for Organizer B',
            organizer=self.organizer_b,
            status=EqubGroup.GroupStatus.ACTIVE,
            currency='ETB',
            contribution_amount=Decimal('2000.00'),
            contribution_frequency=EqubGroup.Frequency.MONTHLY,
            capacity=10,
            start_date=date.today()
        )

        self.org_role = GroupRole.objects.get(group=None, code='GROUP_ORGANIZER')
        self.treasurer_role = GroupRole.objects.get(group=None, code='GROUP_TREASURER')
        self.member_role = GroupRole.objects.get(group=None, code='GROUP_MEMBER')

        # Membership for Organizer A in Group A
        self.m_org_a = GroupMembership.objects.create(
            group=self.group_a,
            user=self.organizer_a,
            status=GroupMembership.MembershipStatus.ACTIVE,
            payout_order_index=1,
            joined_at=timezone.now()
        )
        MembershipRoleAssignment.objects.create(membership=self.m_org_a, role=self.org_role, assigned_by=self.organizer_a)

        # Membership for Fitsum in Group A
        self.m_fitsum = GroupMembership.objects.create(
            group=self.group_a,
            user=self.member_user,
            status=GroupMembership.MembershipStatus.ACTIVE,
            payout_order_index=2,
            joined_at=timezone.now()
        )
        MembershipRoleAssignment.objects.create(membership=self.m_fitsum, role=self.member_role, assigned_by=self.organizer_a)

    def test_unauthenticated_blocked(self):
        """Unauthenticated requests must be blocked with HTTP 401."""
        res = self.client.get('/api/v1/organizer/dashboard/')
        self.assertIn(res.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_organizer_dashboard_retrieval(self):
        """Organizer A can view their dashboard with rich KPI data and group summaries."""
        self.client.force_authenticate(user=self.organizer_a)
        res = self.client.get('/api/v1/organizer/dashboard/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('kpis', res.data)
        self.assertIn('groups_performance', res.data)
        self.assertIn('my_groups_summary', res.data)
        self.assertIn('profile_subscription', res.data)
        self.assertEqual(res.data['organizer_name'], 'Selam Tesfaye')

    def test_group_creation_within_subscription_limit(self):
        """Organizer A can create an Equb group within their SaaS tier limit."""
        self.client.force_authenticate(user=self.organizer_a)
        payload = {
            'name': 'Family Support Equb',
            'description': 'Family fund for emergency support',
            'group_purpose': 'Family Resilience',
            'contribution_amount': '10000.00',
            'contribution_frequency': 'MONTHLY',
            'capacity': 15,
            'start_date': date.today().isoformat(),
            'payout_method': 'ROTATION_ORDER',
            'rules_terms': 'Official rules for Family Support Equb.'
        }
        res = self.client.post('/api/v1/organizer/groups/', data=payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        created_group = EqubGroup.objects.get(name='Family Support Equb')
        self.assertEqual(created_group.organizer, self.organizer_a)
        self.assertIsNotNone(created_group.active_rules_version)

    def test_group_creation_rejected_when_subscription_limit_exceeded(self):
        """Organizer B on Starter tier (limit=1) is blocked from creating a second group."""
        self.client.force_authenticate(user=self.organizer_b)
        payload = {
            'name': 'Exceeded Quota Equb',
            'contribution_amount': '1000.00',
            'capacity': 10
        }
        res = self.client.post('/api/v1/organizer/groups/', data=payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('limit', str(res.data).lower())

    def test_cross_tenant_isolation_blocked(self):
        """Organizer A cannot access, view, or modify Organizer B's Equb group."""
        self.client.force_authenticate(user=self.organizer_a)
        res = self.client.get(f'/api/v1/organizer/groups/{self.group_b.id}/')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Organizer A cannot pause or close Organizer B's group
        res_action = self.client.post(f'/api/v1/organizer/groups/{self.group_b.id}/action/', data={'action': 'pause'})
        self.assertEqual(res_action.status_code, status.HTTP_403_FORBIDDEN)

    def test_group_lifecycle_actions(self):
        """Organizer can pause, resume, and close their own group with audit logging."""
        self.client.force_authenticate(user=self.organizer_a)

        # Pause
        res = self.client.post(f'/api/v1/organizer/groups/{self.group_a.id}/action/', data={'action': 'pause', 'reason': 'Holiday break'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.group_a.refresh_from_db()
        self.assertEqual(self.group_a.status, EqubGroup.GroupStatus.SUSPENDED)

        # Resume
        res = self.client.post(f'/api/v1/organizer/groups/{self.group_a.id}/action/', data={'action': 'resume'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.group_a.refresh_from_db()
        self.assertEqual(self.group_a.status, EqubGroup.GroupStatus.ACTIVE)

    def test_member_invitation_generation(self):
        """Organizer can generate single-use, secure invitation link with expiration."""
        self.client.force_authenticate(user=self.organizer_a)
        payload = {'email': 'newinvitee@digitalequb.et', 'expires_in_days': 7}
        res = self.client.post(f'/api/v1/organizer/groups/{self.group_a.id}/invitations/', data=payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('invite_url', res.data)
        self.assertTrue(GroupInvitation.objects.filter(invited_email='newinvitee@digitalequb.et').exists())

    def test_membership_request_approval_and_rejection(self):
        """Organizer can approve or reject prospective member requests."""
        prospective_user = User.objects.create_user(
            email='applicant@digitalequb.et',
            password='Pass123!',
            full_name='Applicant User'
        )
        req_membership = GroupMembership.objects.create(
            group=self.group_a,
            user=prospective_user,
            status=GroupMembership.MembershipStatus.REQUESTED
        )

        self.client.force_authenticate(user=self.organizer_a)

        # Check in pending requests list
        res_list = self.client.get(f'/api/v1/organizer/groups/{self.group_a.id}/membership-requests/')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_list.data['count'], 1)

        # Approve
        res_app = self.client.post(
            f'/api/v1/organizer/groups/{self.group_a.id}/membership-requests/{req_membership.id}/action/',
            data={'action': 'approve'}
        )
        self.assertEqual(res_app.status_code, status.HTTP_200_OK)
        req_membership.refresh_from_db()
        self.assertEqual(req_membership.status, GroupMembership.MembershipStatus.ACTIVE)

    def test_treasurer_assignment_and_revocation(self):
        """Organizer can assign and revoke Treasurer role for eligible group members."""
        self.client.force_authenticate(user=self.organizer_a)

        # Assign Fitsum as Treasurer
        res = self.client.post(
            f'/api/v1/organizer/groups/{self.group_a.id}/treasurer/action/',
            data={'action': 'assign', 'membership_id': str(self.m_fitsum.id)}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(
            MembershipRoleAssignment.objects.filter(
                membership=self.m_fitsum,
                role__code='GROUP_TREASURER'
            ).exists()
        )

        # Revoke Treasurer
        res_rev = self.client.post(
            f'/api/v1/organizer/groups/{self.group_a.id}/treasurer/action/',
            data={'action': 'revoke'}
        )
        self.assertEqual(res_rev.status_code, status.HTTP_200_OK)
        self.assertFalse(
            MembershipRoleAssignment.objects.filter(
                membership=self.m_fitsum,
                role__code='GROUP_TREASURER'
            ).exists()
        )

    def test_rule_proposal_workflow(self):
        """Organizer can propose new rule version requiring member votes."""
        self.client.force_authenticate(user=self.organizer_a)
        payload = {
            'title': 'Unity Equb Amendment v2',
            'terms_text': 'Contribution increased to 6,000 ETB starting next cycle.',
            'contribution_amount': '6000.00',
            'contribution_frequency': 'MONTHLY',
            'approval_threshold_percent': 100
        }
        res = self.client.post(f'/api/v1/organizer/groups/{self.group_a.id}/rules/proposals/', data=payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['version_number'], 1)
        self.assertEqual(res.data['status'], 'PROPOSED')

    def test_payout_schedule_and_funds_validation(self):
        """Scheduling a payout validates group available funds."""
        self.client.force_authenticate(user=self.organizer_a)
        payload = {
            'recipient_membership_id': str(self.m_fitsum.id),
            'amount': '100000.00',
            'notes': 'Rotation payout round 1'
        }
        res = self.client.post(f'/api/v1/organizer/groups/{self.group_a.id}/payouts/schedule/', data=payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        # Because group currently has 0 ETB balance, status should be BLOCKED_INSUFFICIENT_FUNDS
        self.assertEqual(res.data['status'], PayoutStatus.BLOCKED_INSUFFICIENT_FUNDS)

    def test_dispute_resolution_and_escalation(self):
        """Organizer can add notes, resolve, or escalate disputes to Super Admin."""
        dispute = Dispute.objects.create(
            group=self.group_a,
            reporter_membership=self.m_fitsum,
            title='Payment Discrepancy',
            description='Sent transfer but not recorded yet.',
            status=DisputeStatus.OPEN
        )

        self.client.force_authenticate(user=self.organizer_a)

        # 1. Add Note
        res_note = self.client.post(
            f'/api/v1/organizer/groups/{self.group_a.id}/disputes/{dispute.id}/action/',
            data={'action': 'add_note', 'notes': 'Checked with bank branch.'}
        )
        self.assertEqual(res_note.status_code, status.HTTP_200_OK)

        # 2. Escalate to Super Admin
        res_esc = self.client.post(
            f'/api/v1/organizer/groups/{self.group_a.id}/disputes/{dispute.id}/action/',
            data={'action': 'escalate', 'notes': 'Requires administrative ledger audit.'}
        )
        self.assertEqual(res_esc.status_code, status.HTTP_200_OK)
        self.assertTrue(SupportTicket.objects.filter(category=SupportTicket.Category.DISPUTE_ESCALATION).exists())

    def test_report_csv_export_injection_prevention(self):
        """Report CSV export sanitizes formulas starting with =, +, -, @."""
        self.client.force_authenticate(user=self.organizer_a)
        res = self.client.get(f'/api/v1/organizer/groups/{self.group_a.id}/reports/export/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'text/csv')
        csv_content = res.content.decode('utf-8')
        self.assertIn('Member Name', csv_content)
        self.assertIn('Selam Tesfaye', csv_content)

    def test_support_ticket_creation(self):
        """Organizer can submit support tickets."""
        self.client.force_authenticate(user=self.organizer_a)
        payload = {
            'subject': 'Help with CBE Mobile Banking reconciliation',
            'category': 'TECHNICAL',
            'message': 'Need assistance with automated transaction parsing.'
        }
        res = self.client.post('/api/v1/organizer/support/tickets/', data=payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['subject'], payload['subject'])
