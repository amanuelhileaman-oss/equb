function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const API_BASE = import.meta.env.VITE_API_URL || '';

async function request(endpoint, options = {}) {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/api/v1/${endpoint}`;
  const url = `${API_BASE}${cleanEndpoint}`;
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {})
  };

  // Attach CSRF token for unsafe methods
  const csrfToken = getCookie('csrftoken') || window.__CSRF_TOKEN__;
  if (csrfToken && !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(options.method?.toUpperCase() || 'GET')) {
    headers['X-CSRFToken'] = csrfToken;
  }

  // Handle FormData vs JSON
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(options.body);
  }

  const config = {
    credentials: 'include',
    ...options,
    headers
  };

  const response = await fetch(url, config);
  let data = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    let errorMsg = 'An error occurred during request.';
    if (data?.message && typeof data.message === 'string' && data.message !== 'An input or validation error occurred.') {
      errorMsg = data.message;
    } else if (data?.detail && typeof data.detail === 'string') {
      errorMsg = data.detail;
    } else if (Array.isArray(data?.detail) && data.detail.length > 0) {
      errorMsg = typeof data.detail[0] === 'string' ? data.detail[0] : (data.detail[0]?.string || JSON.stringify(data.detail[0]));
    } else if (typeof data?.detail === 'object' && data.detail !== null) {
      const parts = Object.entries(data.detail).map(([k, v]) => `${k.replace('_', ' ')}: ${Array.isArray(v) ? v[0] : v}`);
      errorMsg = parts.join('; ') || 'Validation error.';
    } else if (data?.message) {
      errorMsg = data.message;
    } else if (typeof data === 'string') {
      errorMsg = data;
    }
    const error = new Error(errorMsg);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

export const api = {
  // Auth
  login: (credentials) => request('/api/v1/auth/login/', { method: 'POST', body: credentials }),
  register: (userData) => request('/api/v1/auth/register/', { method: 'POST', body: userData }),
  logout: () => request('/api/v1/auth/logout/', { method: 'POST' }),
  getCurrentUser: () => request('/api/v1/auth/me/'),
  updateProfile: (profileData) => request('/api/v1/auth/me/', { method: 'PATCH', body: profileData }),

  // Super Admin Comprehensive API Suite
  // Auth & Security Extensions
  mfaSetup: () => request('/api/v1/auth/mfa/setup/', { method: 'POST' }),
  mfaVerify: (code, secret) => request('/api/v1/auth/mfa/verify/', { method: 'POST', body: { code, secret } }),
  mfaDisable: (password, code) => request('/api/v1/auth/mfa/disable/', { method: 'POST', body: { password, code } }),
  requestPasswordReset: (email) => request('/api/v1/auth/password-reset/request/', { method: 'POST', body: { email } }),
  confirmPasswordReset: (data) => request('/api/v1/auth/password-reset/confirm/', { method: 'POST', body: data }),

  // Super Admin API Suite
  getAdminDashboard: () => request('/api/v1/admin/dashboard/'),
  getAdminUsers: (params = '') => request(`/api/v1/admin/users/${params ? '?' + params : ''}`),
  adminUserAction: (userId, action, reason) => request(`/api/v1/admin/users/${userId}/action/`, { method: 'POST', body: { action, reason } }),
  getAdminOrganizers: (params = '') => request(`/api/v1/admin/organizers/${params ? '?' + params : ''}`),
  getAdminOrganizer: (id) => request(`/api/v1/admin/organizers/${id}/`),
  createAdminOrganizer: (data) => request('/api/v1/admin/organizers/', { method: 'POST', body: data }),
  adminOrganizerAction: (id, action, reason) => request(`/api/v1/admin/organizers/${id}/action/`, { method: 'POST', body: { action, reason } }),
  getAdminGroups: (params = '') => request(`/api/v1/admin/groups/${params ? '?' + params : ''}`),
  getAdminGroup: (id) => request(`/api/v1/admin/groups/${id}/`),
  adminGroupAction: (groupId, action, reason) => request(`/api/v1/admin/groups/${groupId}/action/`, { method: 'POST', body: { action, reason } }),
  getAdminVerifications: (params = '') => request(`/api/v1/admin/verifications/${params ? '?' + params : ''}`),
  adminVerificationAction: (id, action, reason) => request(`/api/v1/admin/verifications/${id}/action/`, { method: 'POST', body: { action, reason } }),
  getAdminPlans: () => request('/api/v1/admin/plans/'),
  createAdminPlan: (data) => request('/api/v1/admin/plans/', { method: 'POST', body: data }),
  updateAdminPlan: (id, data) => request(`/api/v1/admin/plans/${id}/`, { method: 'PATCH', body: data }),
  getAdminSubscriptions: () => request('/api/v1/admin/subscriptions/'),
  adminSubscriptionAction: (id, action, reason, days = 30) => request(`/api/v1/admin/subscriptions/${id}/action/`, { method: 'POST', body: { action, reason, days } }),
  getAdminInvoices: () => request('/api/v1/admin/invoices/'),
  getAdminPaymentProviders: () => request('/api/v1/admin/payment-providers/'),
  adminPaymentProviderAction: (id, action, payload = {}) => request(`/api/v1/admin/payment-providers/${id}/action/`, { method: 'POST', body: { action, ...payload } }),
  getAdminFinancialReports: () => request('/api/v1/admin/reports/financial/'),
  getAdminSecurityEvents: () => request('/api/v1/admin/security-events/'),
  getAdminRolesPermissions: () => request('/api/v1/admin/roles-permissions/'),
  updateAdminRolePermissions: (role_id, permissions) => request('/api/v1/admin/roles-permissions/', { method: 'POST', body: { role_id, permissions } }),
  getAdminDisputes: (params = '') => request(`/api/v1/admin/disputes/${params ? '?' + params : ''}`),
  adminDisputeAction: (id, action, notes) => request(`/api/v1/admin/disputes/${id}/action/`, { method: 'POST', body: { action, notes } }),
  getAdminAuditLogs: (params = '') => request(`/api/v1/admin/audit-logs/${params ? '?' + params : ''}`),
  getAdminAnnouncements: () => request('/api/v1/admin/announcements/'),
  createAdminAnnouncement: (data) => request('/api/v1/admin/announcements/', { method: 'POST', body: data }),
  publishAdminAnnouncement: (id) => request(`/api/v1/admin/announcements/${id}/publish/`, { method: 'POST' }),
  getPlatformSettings: () => request('/api/v1/admin/settings/'),
  updatePlatformSetting: (key, value) => request('/api/v1/admin/settings/', { method: 'PATCH', body: { key, value } }),
  updateAllPlatformSettings: (settings) => request('/api/v1/admin/settings/', { method: 'PATCH', body: { settings } }),
  getAdminSystemHealth: () => request('/api/v1/admin/system-health/'),

  // Organizer Dedicated API Suite
  getOrganizerDashboard: () => request('/api/v1/organizer/dashboard/'),
  getOrganizerGroups: (params = '') => request(`/api/v1/organizer/groups/${params ? '?' + params : ''}`),
  createOrganizerGroup: (groupData) => request('/api/v1/organizer/groups/', { method: 'POST', body: groupData }),
  getOrganizerGroup: (groupId) => request(`/api/v1/organizer/groups/${groupId}/`),
  updateOrganizerGroup: (groupId, data) => request(`/api/v1/organizer/groups/${groupId}/`, { method: 'PATCH', body: data }),
  organizerGroupAction: (groupId, action, reason = '') => request(`/api/v1/organizer/groups/${groupId}/action/`, { method: 'POST', body: { action, reason } }),
  getOrganizerGroupMembers: (groupId, params = '') => request(`/api/v1/organizer/groups/${groupId}/members/${params ? '?' + params : ''}`),
  addOrganizerGroupMember: (groupId, memberData) => request(`/api/v1/organizer/groups/${groupId}/members/`, { method: 'POST', body: typeof memberData === 'string' ? { email: memberData } : memberData }),
  joinOrganizerGroupAsMember: (groupId) => request(`/api/v1/organizer/groups/${groupId}/join/`, { method: 'POST' }),
  getOrganizerGroupMemberDetail: (groupId, membershipId) => request(`/api/v1/organizer/groups/${groupId}/members/${membershipId}/`),
  updateOrganizerGroupMember: (groupId, membershipId, data) => request(`/api/v1/organizer/groups/${groupId}/members/${membershipId}/`, { method: 'PATCH', body: data }),
  getOrganizerGroupInvitations: (groupId) => request(`/api/v1/organizer/groups/${groupId}/invitations/`),
  createOrganizerGroupInvitation: (groupId, email, days = 7) => request(`/api/v1/organizer/groups/${groupId}/invitations/`, { method: 'POST', body: { email, expires_in_days: days } }),
  getOrganizerMembershipRequests: (groupId) => request(`/api/v1/organizer/groups/${groupId}/membership-requests/`),
  organizerMembershipRequestAction: (groupId, membershipId, action, reason = '') => request(`/api/v1/organizer/groups/${groupId}/membership-requests/${membershipId}/action/`, { method: 'POST', body: { action, reason } }),
  getOrganizerTreasurer: (groupId) => request(`/api/v1/organizer/groups/${groupId}/treasurer/`),
  organizerTreasurerAction: (groupId, action, membershipId = null) => request(`/api/v1/organizer/groups/${groupId}/treasurer/action/`, { method: 'POST', body: { action, membership_id: membershipId } }),
  getOrganizerGroupRules: (groupId) => request(`/api/v1/organizer/groups/${groupId}/rules/`),
  proposeOrganizerGroupRule: (groupId, ruleData) => request(`/api/v1/organizer/groups/${groupId}/rules/`, { method: 'POST', body: ruleData }),
  getOrganizerGroupContributions: (groupId, params = '') => request(`/api/v1/organizer/groups/${groupId}/contributions/${params ? '?' + params : ''}`),
  getOrganizerGroupPayouts: (groupId) => request(`/api/v1/organizer/groups/${groupId}/payouts/`),
  scheduleOrganizerGroupPayout: (groupId, payload) => request(`/api/v1/organizer/groups/${groupId}/payouts/`, { method: 'POST', body: payload }),
  getOrganizerGroupDisputes: (groupId) => request(`/api/v1/organizer/groups/${groupId}/disputes/`),
  organizerDisputeAction: (groupId, disputeId, action, notes = '') => request(`/api/v1/organizer/groups/${groupId}/disputes/${disputeId}/action/`, { method: 'POST', body: { action, notes } }),
  getOrganizerGroupAnnouncements: (groupId) => request(`/api/v1/organizer/groups/${groupId}/announcements/`),
  createOrganizerGroupAnnouncement: (groupId, payload) => request(`/api/v1/organizer/groups/${groupId}/announcements/`, { method: 'POST', body: payload }),
  getOrganizerVerification: () => request('/api/v1/organizer/verification/'),
  submitOrganizerVerification: (payload) => request('/api/v1/organizer/verification/submit/', { method: 'POST', body: payload }),
  getOrganizerGroupReports: (groupId) => request(`/api/v1/organizer/groups/${groupId}/reports/`),
  getOrganizerGroupReportExportUrl: (groupId) => `/api/v1/organizer/groups/${groupId}/reports/export/`,
  getOrganizerProfile: () => request('/api/v1/organizer/profile/'),
  updateOrganizerProfile: (data) => request('/api/v1/organizer/profile/', { method: 'PATCH', body: data }),
  getOrganizerSupportTickets: () => request('/api/v1/organizer/support/tickets/'),
  createOrganizerSupportTicket: (data) => request('/api/v1/organizer/support/tickets/', { method: 'POST', body: data }),
  getOrganizerSubscription: () => request('/api/v1/organizer/subscription/'),
  payOrganizerSubscription: (data) => request('/api/v1/organizer/subscription/pay/', { method: 'POST', body: data }),
  verifyOrganizerSubscription: (txRef) => request('/api/v1/organizer/subscription/pay/', { method: 'POST', body: { action: 'verify', tx_ref: txRef } }),
  upgradeOrganizerSubscription: (planId) => request('/api/v1/organizer/subscription/upgrade-request/', { method: 'POST', body: { plan_id: planId } }),
  renewOrganizerSubscription: () => request('/api/v1/organizer/subscription/', { method: 'POST', body: { action: 'renew' } }),

  // Legacy / Direct Groups (Preserved)
  getGroups: () => request('/api/v1/groups/'),
  createGroup: (groupData) => request('/api/v1/groups/', { method: 'POST', body: groupData }),
  getGroup: (groupId) => request(`/api/v1/groups/${groupId}/`),
  updateGroup: (groupId, data) => request(`/api/v1/groups/${groupId}/`, { method: 'PATCH', body: data }),
  getGroupMembers: (groupId) => request(`/api/v1/groups/${groupId}/members/`),
  inviteMember: (groupId, email, autoActivate = false) => request(`/api/v1/groups/${groupId}/members/`, { method: 'POST', body: { email, auto_activate: autoActivate } }),
  assignRole: (groupId, membershipId, roleCode) => request(`/api/v1/groups/${groupId}/members/${membershipId}/roles/`, { method: 'POST', body: { role_code: roleCode } }),
  getGroupRules: (groupId) => request(`/api/v1/groups/${groupId}/rules/`),
  proposeRule: (groupId, ruleData) => request(`/api/v1/groups/${groupId}/rules/`, { method: 'POST', body: ruleData }),
  voteRule: (ruleId, decision, comment = '') => request(`/api/v1/rules/${ruleId}/vote/`, { method: 'POST', body: { decision, comment } }),

  // Treasurer
  getTreasurerDashboard: (groupId = '') => request(`/api/v1/treasurer/dashboard/${groupId ? '?group_id=' + groupId : ''}`),
  getTreasurerGroups: () => request('/api/v1/treasurer/groups/'),
  getTreasurerGroupDetail: (groupId) => request(`/api/v1/treasurer/groups/${groupId}/`),
  getTreasurerContributions: (groupId, params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/api/v1/treasurer/groups/${groupId}/contributions/${q ? '?' + q : ''}`);
  },
  getTreasurerCashReceipts: (groupId, status = '') => request(`/api/v1/treasurer/groups/${groupId}/cash-receipts/${status ? '?status=' + status : ''}`),
  treasurerRecordCash: (groupId, data) => request(`/api/v1/treasurer/groups/${groupId}/cash-receipts/`, { method: 'POST', body: data }),
  getTreasurerCashReceiptDetail: (receiptId) => request(`/api/v1/treasurer/cash-receipts/${receiptId}/`),
  getTreasurerReconciliation: (groupId) => request(`/api/v1/treasurer/groups/${groupId}/reconciliation/`),
  treasurerReconcileMatch: (groupId, data) => request(`/api/v1/treasurer/groups/${groupId}/reconciliation/match/`, { method: 'POST', body: data }),
  treasurerFlagException: (groupId, data) => request(`/api/v1/treasurer/groups/${groupId}/reconciliation/exceptions/`, { method: 'POST', body: data }),
  getTreasurerApprovals: () => request('/api/v1/treasurer/approvals/'),
  treasurerApprovalAction: (type, itemId, decision, reason = '') => request(`/api/v1/treasurer/approvals/${type}/${itemId}/action/`, { method: 'POST', body: { decision, reason } }),
  getTreasurerPayouts: (groupId) => request(`/api/v1/treasurer/groups/${groupId}/payouts/`),
  treasurerRequestPayout: (groupId, data) => request(`/api/v1/treasurer/groups/${groupId}/payouts/requests/`, { method: 'POST', body: data }),
  treasurerExecutePayout: (payoutId, data) => request(`/api/v1/treasurer/payouts/${payoutId}/execution-evidence/`, { method: 'POST', body: data }),
  getTreasurerReports: (groupId) => request(`/api/v1/treasurer/groups/${groupId}/reports/`),
  getTreasurerSettings: () => request('/api/v1/treasurer/settings/'),
  updateTreasurerSettings: (data) => request('/api/v1/treasurer/settings/', { method: 'POST', body: data }),

  getGroupObligations: (groupId, status = '') => request(`/api/v1/groups/${groupId}/obligations/${status ? '?status=' + status : ''}`),
  recordCashReceipt: (groupId, payload) => request(`/api/v1/groups/${groupId}/cash-receipts/`, { method: 'POST', body: payload }),
  confirmCashReceipt: (paymentId, notes = '') => request(`/api/v1/payments/${paymentId}/confirm-cash/`, { method: 'POST', body: { notes } }),
  reconcileBankTransfer: (paymentId, decision, notes = '') => request(`/api/v1/payments/${paymentId}/reconcile-transfer/`, { method: 'POST', body: { decision, notes } }),
  getGroupPayments: (groupId, params = '') => request(`/api/v1/groups/${groupId}/payments/${params ? '?' + params : ''}`),
  getGroupPaymentDestinations: (groupId) => request(`/api/v1/groups/${groupId}/destinations/`),
  getSupportedBanks: () => request('/api/v1/payments/banks/'),
  getGroupSubaccount: (groupId) => request(`/api/v1/groups/${groupId}/subaccount/`),
  linkGroupSubaccount: (groupId, data) => request(`/api/v1/groups/${groupId}/subaccount/`, { method: 'POST', body: data }),

  // Payouts
  getGroupPayouts: (groupId) => request(`/api/v1/groups/${groupId}/payouts/`),
  requestPayout: (groupId, payload) => request(`/api/v1/groups/${groupId}/payouts/`, { method: 'POST', body: payload }),
  approvePayout: (payoutId, decision, reason = '') => request(`/api/v1/payouts/${payoutId}/approve/`, { method: 'POST', body: { decision, reason } }),
  executePayout: (payoutId, executionReference, notes = '') => request(`/api/v1/payouts/${payoutId}/execute/`, { method: 'POST', body: { execution_reference: executionReference, notes } }),

  // Member Portal Endpoints
  getMemberDashboard: () => request('/api/v1/member/dashboard/'),
  getMemberGroups: () => request('/api/v1/member/groups/'),
  getMemberGroupDetail: (groupId) => request(`/api/v1/member/groups/${groupId}/`),
  getMemberInvitations: () => request('/api/v1/member/invitations/'),
  acceptMemberInvitation: (id, token = '') => request(`/api/v1/member/invitations/${id ? id + '/action/' : 'action/'}`, { method: 'POST', body: { action: 'accept', token } }),
  declineMemberInvitation: (id, token = '') => request(`/api/v1/member/invitations/${id ? id + '/action/' : 'action/'}`, { method: 'POST', body: { action: 'decline', token } }),
  requestMemberJoinGroup: (groupId) => request(`/api/v1/member/groups/${groupId}/membership-requests/`, { method: 'POST' }),
  getMemberContributions: (params = '') => request(`/api/v1/member/contributions/${params ? '?' + params : ''}`),
  getMyObligations: () => request('/api/v1/member/contributions/'),
  payDigital: (obligationId, providerName = 'CHAPA') => request(`/api/v1/member/obligations/${obligationId}/pay-digital/`, { method: 'POST', body: { provider_name: providerName } }),
  verifyChapaPayment: (txRef) => request('/api/v1/payments/chapa/verify/', { method: 'POST', body: { tx_ref: txRef } }),
  submitBankTransfer: (obligationId, payload) => request(`/api/v1/member/obligations/${obligationId}/submit-transfer/`, { method: 'POST', body: payload }),
  getMemberPayments: (params = '') => request(`/api/v1/member/payments/${params ? '?' + params : ''}`),
  getMemberReceipt: (receiptId) => request(`/api/v1/member/receipts/${receiptId}/`),
  getMyReceipts: () => request('/api/v1/member/receipts/'),
  getMemberPayoutSchedule: () => request('/api/v1/member/payout-schedule/'),
  getMyPayouts: () => request('/api/v1/member/payout-schedule/'),
  getMemberRules: (groupId) => request(`/api/v1/member/groups/${groupId}/rules/`),
  voteMemberRule: (groupId, versionId, decision, comment = '') => request(`/api/v1/member/groups/${groupId}/rules/${versionId}/vote/`, { method: 'POST', body: { decision, comment } }),
  getMemberAnnouncements: () => request('/api/v1/member/announcements/'),
  getMemberDisputes: () => request('/api/v1/member/disputes/'),
  getMemberDisputeDetail: (disputeId) => request(`/api/v1/member/disputes/${disputeId}/`),
  createMemberDispute: (payload) => request('/api/v1/member/disputes/', { method: 'POST', body: payload }),
  reopenMemberDispute: (disputeId, reason) => request(`/api/v1/member/disputes/${disputeId}/reopen/`, { method: 'POST', body: { reason } }),
  getMemberNotifications: () => request('/api/v1/member/notifications/'),
  markMemberNotificationRead: (id) => request(`/api/v1/member/notifications/${id}/read/`, { method: 'POST' }),
  markAllMemberNotificationsRead: () => request('/api/v1/member/notifications/mark-all-read/', { method: 'POST' }),
  getMemberProfile: () => request('/api/v1/member/profile/'),
  updateMemberProfile: (payload) => request('/api/v1/member/profile/', { method: 'PATCH', body: payload }),
  changeMemberPassword: (old_password, new_password) => request('/api/v1/member/profile/', { method: 'POST', body: { old_password, new_password } }),

  // Disputes
  getDisputes: (groupId = '') => request(`/api/v1/disputes/${groupId ? '?group_id=' + groupId : ''}`),
  createDispute: (payload) => request('/api/v1/disputes/', { method: 'POST', body: payload }),
  updateDispute: (disputeId, payload) => request(`/api/v1/disputes/${disputeId}/`, { method: 'PATCH', body: payload }),

  // Subscriptions
  getCurrentSubscription: () => request('/api/v1/subscriptions/current/'),
  getPlans: () => request('/api/v1/subscriptions/plans/'),
  subscribePlan: (planCode) => request('/api/v1/subscriptions/subscribe/', { method: 'POST', body: { plan_code: planCode } }),
  getInvoices: () => request('/api/v1/subscriptions/invoices/'),

  // Notifications
  getNotifications: () => request('/api/v1/notifications/'),
  markNotificationRead: (id) => request(`/api/v1/notifications/${id}/mark-read/`, { method: 'POST' }),
  markAllNotificationsRead: () => request('/api/v1/notifications/mark-all-read/', { method: 'POST' }),

  // Exports
  getExportLedgerUrl: (groupId) => `/api/v1/groups/${groupId}/export/ledger/`,
  getExportObligationsUrl: (groupId) => `/api/v1/groups/${groupId}/export/obligations/`,

  // Equb Lottery & Cycle Management
  getOrganizerLottery: (groupId) => request(`/api/v1/organizer/groups/${groupId}/lottery/`),
  triggerOrganizerLotteryDraw: (groupId, force = false) => request(`/api/v1/organizer/groups/${groupId}/lottery/draw/`, { method: 'POST', body: { force } }),
  startOrganizerNextCycle: (groupId) => request(`/api/v1/organizer/groups/${groupId}/cycles/start-next/`, { method: 'POST' }),
  getMemberLottery: (groupId) => request(`/api/v1/member/groups/${groupId}/lottery/`),

  // Overdue Contributions Resolution System (Dropdown 2: A, B, C)
  getOrganizerOverdueCases: (groupId) => request(`/api/v1/organizer/groups/${groupId}/overdue-cases/`),
  evaluateOrganizerOverdueCases: (groupId) => request(`/api/v1/organizer/groups/${groupId}/overdue-cases/`, { method: 'POST' }),
  resolveOrganizerOverdueCase: (groupId, caseId, data) => request(`/api/v1/organizer/groups/${groupId}/overdue-cases/${caseId}/resolve/`, { method: 'POST', body: data }),
  recordOrganizerReviewDecision: (groupId, reviewId, data) => request(`/api/v1/organizer/groups/${groupId}/membership-reviews/${reviewId}/decide/`, { method: 'POST', body: data }),
  getTreasurerOverdueMonitoring: (groupId) => request(`/api/v1/treasurer/groups/${groupId}/overdue-monitoring/`),
  getMemberPaymentAgreements: () => request('/api/v1/member/payment-agreements/'),
  respondMemberPaymentAgreement: (agreementId, accept, notes = '') => request(`/api/v1/member/payment-agreements/${agreementId}/respond/`, { method: 'POST', body: { accept, notes } }),
};
