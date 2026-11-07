from django.urls import path
from apps.accounts.views import (
    RegisterView, LoginView, LogoutView, CurrentUserView,
    MfaSetupView, MfaVerifyView, MfaDisableView,
    PasswordResetRequestView, PasswordResetConfirmView
)
from apps.groups.views import (
    GroupListCreateView, GroupDetailView, GroupMembersView, AssignMemberRoleView
)
from apps.rules.views import (
    RuleListProposeView, RuleVoteView
)
from apps.contributions.views import (
    GroupObligationsListView, MemberObligationsListView
)
from apps.payments.views import (
    DigitalPaymentInitiateView, CashReceiptRecordView, CashReceiptConfirmView,
    BankTransferSubmitView, BankTransferReconcileView, ProviderWebhookView,
    GroupPaymentsListView, MemberReceiptsListView, GroupPaymentDestinationsView,
    ChapaPaymentVerifyView, ChapaSupportedBanksView, GroupChapaSubaccountView
)
from apps.payouts.views import (
    GroupPayoutsView, PayoutApprovalView, PayoutExecutionView, MemberPayoutsView
)
from apps.disputes.views import (
    DisputeListCreateView, DisputeDetailView
)
from apps.subscriptions.views import (
    PlanListView, CurrentSubscriptionView, SubscribePlanView, SubscriptionInvoicesView
)
from apps.audit_app.views import (
    SuperAdminDashboardView, AdminUsersListView, AdminUserActionView,
    AdminGroupsListView, AdminGroupDetailView, AdminGroupActionView,
    AdminOrganizersListView, AdminOrganizerDetailView, AdminOrganizerActionView,
    AdminVerificationsListView, AdminVerificationActionView,
    AdminPlansManagementView, AdminPlanDetailView,
    AdminSubscriptionsListView, AdminSubscriptionActionView, AdminInvoicesListView,
    AdminPaymentProvidersView, AdminPaymentProviderActionView,
    AdminFinancialReportsView, AdminFinancialReportsExportCSVView,
    AdminSecurityEventsView, AdminRolesPermissionsView,
    AdminSecurityIncidentsView, AdminSecurityIncidentDetailView,
    AdminSecurityIncidentActionView, AdminSecurityIncidentNotifyGroupView,
    AdminDisputesListView, AdminDisputeActionView,
    AdminAuditLogsView, AdminAuditLogsExportCSVView,
    AdminAnnouncementsView, AdminAnnouncementActionView,
    PlatformSettingsView, AdminSystemHealthView
)
from apps.common.dashboard_views import (
    OrganizerDashboardView, TreasurerDashboardView, MemberDashboardView
)
from apps.common.organizer_views import (
    OrganizerGroupsListView, OrganizerGroupDetailView, OrganizerGroupLifecycleActionView,
    OrganizerGroupMembersView, OrganizerGroupMemberDetailView, OrganizerGroupMembersImportView, OrganizerGroupJoinView, OrganizerGroupInvitationsView, OrganizerGroupMembershipRequestsView,
    OrganizerGroupTreasurerView, OrganizerGroupRulesView, OrganizerGroupContributionsView,
    OrganizerGroupPayoutsView, OrganizerGroupDisputesView, OrganizerGroupAnnouncementsView,
    OrganizerVerificationStatusView, OrganizerGroupReportsView, OrganizerGroupReportsExportCSVView,
    OrganizerProfileView, OrganizerSupportTicketsView, OrganizerSubscriptionManagementView,
    OrganizerSubscriptionPayView
)
from apps.common.treasurer_views import (
    TreasurerDashboardOverviewView, TreasurerGroupsListView, TreasurerGroupDetailView,
    TreasurerContributionsListView, TreasurerCashReceiptsView, TreasurerCashReceiptDetailView,
    TreasurerReconciliationView, TreasurerReconciliationActionView, TreasurerReconciliationExceptionView,
    TreasurerApprovalsView, TreasurerApprovalActionView, TreasurerPayoutsView,
    TreasurerPayoutExecutionView, TreasurerFinancialReportsView, TreasurerFinancialReportsExportCSVView,
    TreasurerSettingsView
)
from apps.common.member_views import (
    MemberDashboardOverviewView, MemberGroupsListView, MemberGroupDetailView,
    MemberInvitationsView, MemberMembershipRequestView,
    MemberContributionsListView, MemberPaymentsListView, MemberReceiptDetailView,
    MemberPayoutScheduleView, MemberRulesView, MemberAnnouncementsView,
    MemberDisputesListView, MemberDisputeDetailView, MemberDisputeReopenView,
    MemberNotificationsView, MemberProfileView
)
from apps.notifications.views import (
    NotificationListView, NotificationMarkReadView, NotificationMarkAllReadView
)
from apps.groups.lottery_views import (
    OrganizerGroupLotteryView, OrganizerTriggerLotteryDrawView,
    OrganizerStartNextCycleView, MemberGroupLotteryView
)
from apps.groups.overdue_views import (
    OrganizerOverdueCasesView, OrganizerResolveOverdueCaseView,
    OrganizerRecordReviewDecisionView, MemberPaymentAgreementsView,
    TreasurerOverdueMonitoringView
)
from apps.common.export_views import (
    GroupLedgerExportCSVView, GroupObligationsExportCSVView
)

urlpatterns = [
    # Authentication & Session
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('auth/me/', CurrentUserView.as_view(), name='auth-me'),
    path('auth/mfa/setup/', MfaSetupView.as_view(), name='auth-mfa-setup'),
    path('auth/mfa/verify/', MfaVerifyView.as_view(), name='auth-mfa-verify'),
    path('auth/mfa/disable/', MfaDisableView.as_view(), name='auth-mfa-disable'),
    path('auth/password-reset/request/', PasswordResetRequestView.as_view(), name='auth-password-reset-request'),
    path('auth/password-reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm'),
    path('auth/password/reset/request/', PasswordResetRequestView.as_view(), name='auth-password-reset-request-alias'),
    path('auth/password/reset/confirm/', PasswordResetConfirmView.as_view(), name='auth-password-reset-confirm-alias'),

    # Super Admin Dashboard & All 14 Dedicated Modules
    path('admin/dashboard/', SuperAdminDashboardView.as_view(), name='admin-dashboard'),
    path('admin/organizers/', AdminOrganizersListView.as_view(), name='admin-organizers-list'),
    path('admin/organizers/<uuid:user_id>/', AdminOrganizerDetailView.as_view(), name='admin-organizer-detail'),
    path('admin/organizers/<uuid:user_id>/action/', AdminOrganizerActionView.as_view(), name='admin-organizer-action'),
    path('admin/groups/', AdminGroupsListView.as_view(), name='admin-groups-list'),
    path('admin/groups/<uuid:group_id>/', AdminGroupDetailView.as_view(), name='admin-group-detail'),
    path('admin/groups/<uuid:group_id>/action/', AdminGroupActionView.as_view(), name='admin-group-action'),
    path('admin/verifications/', AdminVerificationsListView.as_view(), name='admin-verifications-list'),
    path('admin/verifications/<uuid:record_id>/action/', AdminVerificationActionView.as_view(), name='admin-verification-action'),
    path('admin/plans/', AdminPlansManagementView.as_view(), name='admin-plans'),
    path('admin/plans/<uuid:plan_id>/', AdminPlanDetailView.as_view(), name='admin-plan-detail'),
    path('admin/subscriptions/', AdminSubscriptionsListView.as_view(), name='admin-subscriptions-list'),
    path('admin/subscriptions/<uuid:sub_id>/action/', AdminSubscriptionActionView.as_view(), name='admin-subscription-action'),
    path('admin/invoices/', AdminInvoicesListView.as_view(), name='admin-invoices-list'),
    path('admin/payment-providers/', AdminPaymentProvidersView.as_view(), name='admin-payment-providers'),
    path('admin/payment-providers/<uuid:provider_id>/action/', AdminPaymentProviderActionView.as_view(), name='admin-payment-provider-action'),
    path('admin/reports/financial/', AdminFinancialReportsView.as_view(), name='admin-reports-financial'),
    path('admin/reports/financial/export/', AdminFinancialReportsExportCSVView.as_view(), name='admin-reports-financial-export'),
    path('admin/reports/export/', AdminFinancialReportsExportCSVView.as_view(), name='admin-reports-export'),
    path('admin/users/', AdminUsersListView.as_view(), name='admin-users-list'),
    path('admin/users/<uuid:user_id>/action/', AdminUserActionView.as_view(), name='admin-user-action'),
    path('admin/security-events/', AdminSecurityEventsView.as_view(), name='admin-security-events'),
    path('admin/security/incidents/', AdminSecurityIncidentsView.as_view(), name='admin-security-incidents'),
    path('admin/security/incidents/<str:incident_id>/', AdminSecurityIncidentDetailView.as_view(), name='admin-security-incident-detail'),
    path('admin/security/incidents/<str:incident_id>/action/', AdminSecurityIncidentActionView.as_view(), name='admin-security-incident-action'),
    path('admin/security/incidents/<str:incident_id>/notify-group/', AdminSecurityIncidentNotifyGroupView.as_view(), name='admin-security-incident-notify-group'),
    path('admin/security-incidents/', AdminSecurityIncidentsView.as_view()),
    path('admin/security-incidents/<str:incident_id>/', AdminSecurityIncidentDetailView.as_view()),
    path('admin/security-incidents/<str:incident_id>/action/', AdminSecurityIncidentActionView.as_view()),
    path('admin/security-incidents/<str:incident_id>/notify-group/', AdminSecurityIncidentNotifyGroupView.as_view()),
    path('admin/roles-permissions/', AdminRolesPermissionsView.as_view(), name='admin-roles-permissions'),
    path('admin/disputes/', AdminDisputesListView.as_view(), name='admin-disputes-list'),
    path('admin/disputes/<uuid:dispute_id>/action/', AdminDisputeActionView.as_view(), name='admin-dispute-action'),
    path('admin/audit-logs/', AdminAuditLogsView.as_view(), name='admin-audit-logs'),
    path('admin/audit-logs/export/', AdminAuditLogsExportCSVView.as_view(), name='admin-audit-logs-export'),
    path('admin/announcements/', AdminAnnouncementsView.as_view(), name='admin-announcements'),
    path('admin/announcements/<uuid:announcement_id>/publish/', AdminAnnouncementActionView.as_view(), name='admin-announcement-publish'),
    path('admin/settings/', PlatformSettingsView.as_view(), name='admin-settings'),
    path('admin/system-health/', AdminSystemHealthView.as_view(), name='admin-system-health'),

    # Dedicated Organizer Dashboard & 10 Modules Endpoints
    path('organizer/dashboard/', OrganizerDashboardView.as_view(), name='organizer-dashboard'),
    path('organizer/groups/', OrganizerGroupsListView.as_view(), name='organizer-groups-list'),
    path('organizer/groups/<uuid:group_id>/', OrganizerGroupDetailView.as_view(), name='organizer-group-detail'),
    path('organizer/groups/<uuid:group_id>/action/', OrganizerGroupLifecycleActionView.as_view(), name='organizer-group-action'),
    path('organizer/groups/<uuid:group_id>/members/', OrganizerGroupMembersView.as_view(), name='organizer-group-members'),
    path('organizer/groups/<uuid:group_id>/join/', OrganizerGroupJoinView.as_view(), name='organizer-group-join'),
    path('organizer/groups/<uuid:group_id>/members/<uuid:membership_id>/', OrganizerGroupMemberDetailView.as_view(), name='organizer-group-member-detail'),
    path('organizer/groups/<uuid:group_id>/members/import/', OrganizerGroupMembersImportView.as_view(), name='organizer-group-members-import'),
    path('organizer/groups/<uuid:group_id>/invitations/', OrganizerGroupInvitationsView.as_view(), name='organizer-group-invitations'),
    path('organizer/groups/<uuid:group_id>/membership-requests/', OrganizerGroupMembershipRequestsView.as_view(), name='organizer-group-membership-requests'),
    path('organizer/groups/<uuid:group_id>/membership-requests/<uuid:membership_id>/action/', OrganizerGroupMembershipRequestsView.as_view(), name='organizer-group-membership-request-action'),
    path('organizer/groups/<uuid:group_id>/treasurer/', OrganizerGroupTreasurerView.as_view(), name='organizer-group-treasurer'),
    path('organizer/groups/<uuid:group_id>/treasurer/action/', OrganizerGroupTreasurerView.as_view(), name='organizer-group-treasurer-action'),
    path('organizer/groups/<uuid:group_id>/rules/', OrganizerGroupRulesView.as_view(), name='organizer-group-rules'),
    path('organizer/groups/<uuid:group_id>/rules/proposals/', OrganizerGroupRulesView.as_view(), name='organizer-group-rules-proposals'),
    path('organizer/groups/<uuid:group_id>/contributions/', OrganizerGroupContributionsView.as_view(), name='organizer-group-contributions'),
    path('organizer/groups/<uuid:group_id>/payouts/', OrganizerGroupPayoutsView.as_view(), name='organizer-group-payouts'),
    path('organizer/groups/<uuid:group_id>/payouts/schedule/', OrganizerGroupPayoutsView.as_view(), name='organizer-group-payouts-schedule'),
    path('organizer/groups/<uuid:group_id>/disputes/', OrganizerGroupDisputesView.as_view(), name='organizer-group-disputes'),
    path('organizer/groups/<uuid:group_id>/disputes/<uuid:dispute_id>/action/', OrganizerGroupDisputesView.as_view(), name='organizer-group-dispute-action'),
    path('organizer/groups/<uuid:group_id>/announcements/', OrganizerGroupAnnouncementsView.as_view(), name='organizer-group-announcements'),
    path('organizer/verification/', OrganizerVerificationStatusView.as_view(), name='organizer-verification'),
    path('organizer/verification/submit/', OrganizerVerificationStatusView.as_view(), name='organizer-verification-submit'),
    path('organizer/groups/<uuid:group_id>/reports/', OrganizerGroupReportsView.as_view(), name='organizer-group-reports'),
    path('organizer/groups/<uuid:group_id>/reports/export/', OrganizerGroupReportsExportCSVView.as_view(), name='organizer-group-reports-export'),
    path('organizer/profile/', OrganizerProfileView.as_view(), name='organizer-profile'),
    path('organizer/support/tickets/', OrganizerSupportTicketsView.as_view(), name='organizer-support-tickets'),
    path('organizer/subscription/', OrganizerSubscriptionManagementView.as_view(), name='organizer-subscription'),
    path('organizer/subscription/pay/', OrganizerSubscriptionPayView.as_view(), name='organizer-subscription-pay'),
    path('organizer/subscription/upgrade-request/', OrganizerSubscriptionManagementView.as_view(), name='organizer-subscription-upgrade'),
    # Treasurer Portal Endpoints
    path('treasurer/dashboard/', TreasurerDashboardOverviewView.as_view(), name='treasurer-dashboard'),
    path('treasurer/groups/', TreasurerGroupsListView.as_view(), name='treasurer-groups-list'),
    path('treasurer/groups/<uuid:group_id>/', TreasurerGroupDetailView.as_view(), name='treasurer-group-detail'),
    path('treasurer/groups/<uuid:group_id>/contributions/', TreasurerContributionsListView.as_view(), name='treasurer-contributions-list'),
    path('treasurer/groups/<uuid:group_id>/cash-receipts/', TreasurerCashReceiptsView.as_view(), name='treasurer-cash-receipts'),
    path('treasurer/cash-receipts/<uuid:receipt_id>/', TreasurerCashReceiptDetailView.as_view(), name='treasurer-cash-receipt-detail'),
    path('treasurer/groups/<uuid:group_id>/reconciliation/', TreasurerReconciliationView.as_view(), name='treasurer-reconciliation'),
    path('treasurer/groups/<uuid:group_id>/reconciliation/match/', TreasurerReconciliationActionView.as_view(), name='treasurer-reconciliation-match'),
    path('treasurer/groups/<uuid:group_id>/reconciliation/exceptions/', TreasurerReconciliationExceptionView.as_view(), name='treasurer-reconciliation-exceptions'),
    path('treasurer/approvals/', TreasurerApprovalsView.as_view(), name='treasurer-approvals'),
    path('treasurer/approvals/<str:approval_type>/<uuid:item_id>/action/', TreasurerApprovalActionView.as_view(), name='treasurer-approval-action'),
    path('treasurer/groups/<uuid:group_id>/payouts/', TreasurerPayoutsView.as_view(), name='treasurer-payouts'),
    path('treasurer/groups/<uuid:group_id>/payouts/requests/', TreasurerPayoutsView.as_view(), name='treasurer-payout-requests'),
    path('treasurer/payouts/<uuid:payout_id>/execution-evidence/', TreasurerPayoutExecutionView.as_view(), name='treasurer-payout-execution-evidence'),
    path('treasurer/groups/<uuid:group_id>/reports/', TreasurerFinancialReportsView.as_view(), name='treasurer-reports'),
    path('treasurer/groups/<uuid:group_id>/reports/export/', TreasurerFinancialReportsExportCSVView.as_view(), name='treasurer-reports-export'),
    path('treasurer/settings/', TreasurerSettingsView.as_view(), name='treasurer-settings'),

    # Dedicated Member Interface Endpoints
    path('member/dashboard/', MemberDashboardOverviewView.as_view(), name='member-dashboard'),
    path('member/groups/', MemberGroupsListView.as_view(), name='member-groups-list'),
    path('member/groups/<uuid:group_id>/', MemberGroupDetailView.as_view(), name='member-group-detail'),
    path('member/groups/<uuid:group_id>/membership-requests/', MemberMembershipRequestView.as_view(), name='member-membership-request'),
    path('member/groups/<uuid:group_id>/rules/', MemberRulesView.as_view(), name='member-group-rules'),
    path('member/groups/<uuid:group_id>/rules/<uuid:version_id>/vote/', MemberRulesView.as_view(), name='member-rule-vote'),
    path('member/invitations/', MemberInvitationsView.as_view(), name='member-invitations-list'),
    path('member/invitations/<uuid:invitation_id>/action/', MemberInvitationsView.as_view(), name='member-invitation-action'),
    path('member/invitations/action/', MemberInvitationsView.as_view(), name='member-invitation-token-action'),
    path('member/contributions/', MemberContributionsListView.as_view(), name='member-contributions-list'),
    path('member/payments/', MemberPaymentsListView.as_view(), name='member-payments-list'),
    path('member/receipts/<str:receipt_id>/', MemberReceiptDetailView.as_view(), name='member-receipt-detail'),
    path('member/payout-schedule/', MemberPayoutScheduleView.as_view(), name='member-payout-schedule'),
    path('member/announcements/', MemberAnnouncementsView.as_view(), name='member-announcements-list'),
    path('member/disputes/', MemberDisputesListView.as_view(), name='member-disputes-list'),
    path('member/disputes/<uuid:dispute_id>/', MemberDisputeDetailView.as_view(), name='member-dispute-detail'),
    path('member/disputes/<uuid:dispute_id>/reopen/', MemberDisputeReopenView.as_view(), name='member-dispute-reopen'),
    path('member/notifications/', MemberNotificationsView.as_view(), name='member-notifications-list'),
    path('member/notifications/<uuid:notification_id>/read/', MemberNotificationsView.as_view(), name='member-notification-read'),
    path('member/notifications/mark-all-read/', MemberNotificationsView.as_view(), name='member-notifications-mark-all-read'),
    path('member/profile/', MemberProfileView.as_view(), name='member-profile'),

    # Groups & Memberships
    path('groups/', GroupListCreateView.as_view(), name='group-list-create'),
    path('groups/<uuid:id>/', GroupDetailView.as_view(), name='group-detail'),
    path('groups/<uuid:group_id>/members/', GroupMembersView.as_view(), name='group-members'),
    path('groups/<uuid:group_id>/members/<uuid:membership_id>/roles/', AssignMemberRoleView.as_view(), name='assign-member-role'),
    path('groups/<uuid:group_id>/destinations/', GroupPaymentDestinationsView.as_view(), name='group-destinations'),

    # Group Rules & Approvals
    path('groups/<uuid:group_id>/rules/', RuleListProposeView.as_view(), name='group-rules'),
    path('rules/<uuid:rule_id>/vote/', RuleVoteView.as_view(), name='rule-vote'),

    # Contributions & Obligations
    path('groups/<uuid:group_id>/obligations/', GroupObligationsListView.as_view(), name='group-obligations'),
    path('member/obligations/', MemberObligationsListView.as_view(), name='member-obligations'),

    # Payments (Method A, B, C) & Chapa Verification
    path('payments/banks/', ChapaSupportedBanksView.as_view(), name='chapa-banks'),
    path('groups/<uuid:group_id>/subaccount/', GroupChapaSubaccountView.as_view(), name='group-chapa-subaccount'),
    path('payments/chapa/verify/', ChapaPaymentVerifyView.as_view(), name='chapa-verify'),
    path('member/obligations/<uuid:obligation_id>/pay-digital/', DigitalPaymentInitiateView.as_view(), name='pay-digital'),
    path('member/obligations/<uuid:obligation_id>/submit-transfer/', BankTransferSubmitView.as_view(), name='submit-transfer'),
    path('groups/<uuid:group_id>/cash-receipts/', CashReceiptRecordView.as_view(), name='cash-receipt-record'),
    path('payments/<uuid:payment_id>/confirm-cash/', CashReceiptConfirmView.as_view(), name='cash-receipt-confirm'),
    path('payments/<uuid:payment_id>/reconcile-transfer/', BankTransferReconcileView.as_view(), name='reconcile-transfer'),
    path('groups/<uuid:group_id>/payments/', GroupPaymentsListView.as_view(), name='group-payments'),
    path('member/receipts/', MemberReceiptsListView.as_view(), name='member-receipts'),

    # Payouts
    path('groups/<uuid:group_id>/payouts/', GroupPayoutsView.as_view(), name='group-payouts'),
    path('payouts/<uuid:payout_id>/approve/', PayoutApprovalView.as_view(), name='payout-approve'),
    path('payouts/<uuid:payout_id>/execute/', PayoutExecutionView.as_view(), name='payout-execute'),
    path('member/payouts/', MemberPayoutsView.as_view(), name='member-payouts'),

    # Disputes
    path('disputes/', DisputeListCreateView.as_view(), name='disputes-list-create'),
    path('disputes/<uuid:dispute_id>/', DisputeDetailView.as_view(), name='dispute-detail'),

    # Subscriptions
    path('subscriptions/current/', CurrentSubscriptionView.as_view(), name='sub-current'),
    path('subscriptions/plans/', PlanListView.as_view(), name='sub-plans'),
    path('subscriptions/subscribe/', SubscribePlanView.as_view(), name='sub-subscribe'),
    path('subscriptions/invoices/', SubscriptionInvoicesView.as_view(), name='sub-invoices'),

    # Digital Provider Webhooks
    path('webhooks/<str:provider>/', ProviderWebhookView.as_view(), name='provider-webhook'),

    # In-App Notifications
    path('notifications/', NotificationListView.as_view(), name='notifications-list'),
    path('notifications/<uuid:notification_id>/mark-read/', NotificationMarkReadView.as_view(), name='notification-mark-read'),
    path('notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notification-mark-all-read'),

    # CSV Financial & Obligation Exports
    path('groups/<uuid:group_id>/export/ledger/', GroupLedgerExportCSVView.as_view(), name='group-ledger-export'),
    path('groups/<uuid:group_id>/export/obligations/', GroupObligationsExportCSVView.as_view(), name='group-obligations-export'),

    # Digital Equb Lottery & Cycle Management Endpoints
    path('organizer/groups/<uuid:group_id>/lottery/', OrganizerGroupLotteryView.as_view(), name='organizer-group-lottery'),
    path('organizer/groups/<uuid:group_id>/lottery/draw/', OrganizerTriggerLotteryDrawView.as_view(), name='organizer-lottery-draw'),
    path('organizer/groups/<uuid:group_id>/cycles/start-next/', OrganizerStartNextCycleView.as_view(), name='organizer-start-next-cycle'),
    path('member/groups/<uuid:group_id>/lottery/', MemberGroupLotteryView.as_view(), name='member-group-lottery'),

    # Overdue Contribution Resolution System (Dropdown 2: A, B, C)
    path('organizer/groups/<uuid:group_id>/overdue-cases/', OrganizerOverdueCasesView.as_view(), name='organizer-overdue-cases'),
    path('organizer/groups/<uuid:group_id>/overdue-cases/<uuid:case_id>/resolve/', OrganizerResolveOverdueCaseView.as_view(), name='organizer-resolve-overdue-case'),
    path('organizer/groups/<uuid:group_id>/membership-reviews/<uuid:review_id>/decide/', OrganizerRecordReviewDecisionView.as_view(), name='organizer-record-review-decision'),
    path('treasurer/groups/<uuid:group_id>/overdue-monitoring/', TreasurerOverdueMonitoringView.as_view(), name='treasurer-overdue-monitoring'),
    path('member/payment-agreements/', MemberPaymentAgreementsView.as_view(), name='member-payment-agreements'),
    path('member/payment-agreements/<uuid:agreement_id>/respond/', MemberPaymentAgreementsView.as_view(), name='member-payment-agreement-respond'),
]
