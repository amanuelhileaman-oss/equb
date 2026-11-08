import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { HeaderControls } from '../components/HeaderControls';
import { NotificationCenter } from '../components/NotificationCenter';
import { ToastNotification } from '../components/ToastNotification';
import { processAvatarImage } from '../utils/imageHelper';
import './MemberInterface.css';
import {
  Home,
  Users,
  Wallet,
  Clock,
  Gift,
  Megaphone,
  MessageSquare,
  Bell,
  Settings,
  Headphones,
  Search,
  CheckCircle,
  CheckCircle2,
  AlertCircle,
  FileText,
  CreditCard,
  Building,
  DollarSign,
  Calendar,
  Check,
  ChevronRight,
  ChevronDown,
  Trophy,
  Printer,
  X,
  Send,
  ThumbsUp,
  ThumbsDown,
  RefreshCw,
  LogOut,
  HelpCircle,
  Eye,
  Camera,
  Info
} from 'lucide-react';

export function MemberInterface() {
  const { user, setUser, logout, refreshUser } = useAuth();
  const { t, language, setLanguage } = useLanguage();
  const { effectiveTheme } = useTheme();

  // Active navigation tab
  const [activeTab, setActiveTab] = useState('home'); // 'home' | 'groups' | 'contributions' | 'payments' | 'payouts' | 'announcements' | 'disputes' | 'notifications' | 'profile' | 'help'
  const [refreshing, setRefreshing] = useState(false);
  const [memberAgreements, setMemberAgreements] = useState([]);
  const [respondingAgreementId, setRespondingAgreementId] = useState(null);

  // Dashboard Data State
  const [dashboardData, setDashboardData] = useState(null);
  const [groupsList, setGroupsList] = useState([]);
  const [selectedGroupDetail, setSelectedGroupDetail] = useState(null);
  const [groupDetailTab, setGroupDetailTab] = useState('overview'); // 'overview' | 'rules' | 'schedule' | 'payments' | 'payouts' | 'announcements' | 'members' | 'disputes'
  const [invitations, setInvitations] = useState([]);
  const [contributions, setContributions] = useState([]);
  const [payments, setPayments] = useState([]);
  const [payoutSchedule, setPayoutSchedule] = useState({ personal_payouts: [], group_schedules: [] });
  const [announcements, setAnnouncements] = useState([]);
  const [disputes, setDisputes] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [profileData, setProfileData] = useState(null);

  // Loading & Alerts
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Search & Filter States
  const [searchQuery, setSearchQuery] = useState('');
  const [contributionFilter, setContributionFilter] = useState('ALL');
  const [paymentFilter, setPaymentFilter] = useState('ALL');

  // Modals
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [selectedObligationToPay, setSelectedObligationToPay] = useState(null);
  const [paymentMethodChoice, setPaymentMethodChoice] = useState('DIGITAL'); // 'DIGITAL' | 'BANK_TRANSFER' | 'CASH'
  const [transferRef, setTransferRef] = useState('');
  const [transferNotes, setTransferNotes] = useState('');

  const [receiptModalOpen, setReceiptModalOpen] = useState(false);
  const [activeReceiptSlip, setActiveReceiptSlip] = useState(null);

  const [disputeModalOpen, setDisputeModalOpen] = useState(false);
  const [disputeForm, setDisputeForm] = useState({
    group_id: '',
    category: 'PAYMENT_NOT_RECORDED',
    title: '',
    description: ''
  });

  const [rulesModalOpen, setRulesModalOpen] = useState(false);
  const [activeRulesGroup, setActiveRulesGroup] = useState(null);
  const [activeRulesVersions, setActiveRulesVersions] = useState([]);

  // Load Dashboard Overview
  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setErrorMsg('');
      const [data, agrs] = await Promise.all([
        api.getMemberDashboard(),
        api.getMemberPaymentAgreements().catch(() => [])
      ]);
      setDashboardData(data);
      setMemberAgreements(Array.isArray(agrs) ? agrs : (agrs?.results || []));
    } catch (err) {
      setErrorMsg(err.message || 'Failed to load member overview.');
    } finally {
      setLoading(false);
    }
  };

  const loadPaymentAgreements = async () => {
    try {
      const agrs = await api.getMemberPaymentAgreements();
      setMemberAgreements(Array.isArray(agrs) ? agrs : (agrs?.results || []));
    } catch (err) {
      console.error('Failed to load member payment agreements:', err);
    }
  };

  const handleRespondAgreement = async (agreementId, accept) => {
    try {
      setRespondingAgreementId(agreementId);
      const res = await api.respondMemberPaymentAgreement(agreementId, accept);
      setSuccessMsg(res.message || (accept ? 'Payment agreement accepted successfully!' : 'Payment agreement declined.'));
      await loadPaymentAgreements();
      await loadDashboardData();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to respond to payment agreement.');
    } finally {
      setRespondingAgreementId(null);
    }
  };

  const handleRefreshAll = async () => {
    try {
      setRefreshing(true);
      await Promise.all([
        loadDashboardData(),
        loadPaymentAgreements()
      ]);
      setSuccessMsg('Member portal refreshed with latest data.');
      setTimeout(() => setSuccessMsg(''), 3000);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    // Check for return from Chapa payment gateway (handling &amp; encoding safely)
    const rawSearch = window.location.search || '';
    const cleanSearch = rawSearch.replace(/&amp;/g, '&');
    const urlParams = new URLSearchParams(cleanSearch);
    const txRef = urlParams.get('tx_ref') || urlParams.get('amp;tx_ref');

    if (txRef && (txRef.startsWith('EQUB-CHP') || txRef.startsWith('EQUB-'))) {
      const cleanTxRef = String(txRef).split('&')[0].split('?')[0].trim();
      const verifyChapaReturn = async () => {
        try {
          setLoading(true);
          const verRes = await api.verifyChapaPayment(cleanTxRef);
          if (verRes.status === 'CONFIRMED' || verRes.status === 'PAID') {
            setSuccessMsg(`Contribution payment confirmed via Chapa! Receipt: ${verRes.receipt_number || txRef}. Group funds updated.`);
          } else {
            setErrorMsg(`Chapa payment status: ${verRes.status || 'Verification in progress'}.`);
          }
        } catch (err) {
          setErrorMsg(err.message || 'Failed to verify Chapa contribution payment.');
        } finally {
          setLoading(false);
          window.history.replaceState({}, document.title, window.location.pathname);
          loadDashboardData();
        }
      };
      verifyChapaReturn();
    } else {
      loadDashboardData();
    }
  }, []);

  // Load Tab Specific Data
  useEffect(() => {
    const fetchTabContent = async () => {
      try {
        if (activeTab === 'groups') {
          const [grps, invs] = await Promise.all([
            api.getMemberGroups(),
            api.getMemberInvitations()
          ]);
          setGroupsList(grps || []);
          setInvitations(invs || []);
        } else if (activeTab === 'contributions') {
          const obs = await api.getMemberContributions();
          setContributions(obs || []);
        } else if (activeTab === 'payments') {
          const pays = await api.getMemberPayments();
          setPayments(pays || []);
        } else if (activeTab === 'payouts') {
          const po = await api.getMemberPayoutSchedule();
          setPayoutSchedule(po || { personal_payouts: [], group_schedules: [] });
        } else if (activeTab === 'announcements') {
          const anns = await api.getMemberAnnouncements();
          setAnnouncements(anns || []);
        } else if (activeTab === 'disputes') {
          const disps = await api.getMemberDisputes();
          setDisputes(disps || []);
        } else if (activeTab === 'notifications') {
          const notifs = await api.getMemberNotifications();
          setNotifications(notifs || []);
        } else if (activeTab === 'profile') {
          const prof = await api.getMemberProfile();
          setProfileData(prof);
        }
      } catch (err) {
        console.error('Tab loading error:', err);
      }
    };
    fetchTabContent();
  }, [activeTab]);

  // Open Group Detail View
  const handleOpenGroupDetail = async (groupId) => {
    try {
      setLoading(true);
      const detail = await api.getMemberGroupDetail(groupId);
      setSelectedGroupDetail(detail);
      setGroupDetailTab('overview');
      setActiveTab('group-detail');
    } catch (err) {
      alert(err.message || 'Failed to load group details.');
    } finally {
      setLoading(false);
    }
  };

  // Open Rules Modal
  const handleOpenRules = async (group) => {
    try {
      const versions = await api.getMemberRules(group.id);
      setActiveRulesGroup(group);
      setActiveRulesVersions(versions || []);
      setRulesModalOpen(true);
    } catch (err) {
      alert(err.message || 'Failed to load group rules.');
    }
  };

  // Rule Voting
  const handleVoteRule = async (versionId, decision) => {
    try {
      await api.voteMemberRule(activeRulesGroup.id, versionId, decision);
      setSuccessMsg(`Vote '${decision}' recorded successfully.`);
      const versions = await api.getMemberRules(activeRulesGroup.id);
      setActiveRulesVersions(versions || []);
    } catch (err) {
      alert(err.message || 'Voting failed.');
    }
  };

  // Make Payment Handlers
  const handleInitiatePayment = (obligation) => {
    setSelectedObligationToPay(obligation);
    setPaymentMethodChoice('DIGITAL');
    setTransferRef('');
    setTransferNotes('');
    setPaymentModalOpen(true);
  };

  const handleExecutePayment = async () => {
    if (!selectedObligationToPay) return;
    try {
      setLoading(true);
      if (paymentMethodChoice === 'DIGITAL') {
        const res = await api.payDigital(selectedObligationToPay.id, 'CHAPA');
        if (res.checkout_url) {
          setSuccessMsg(`Chapa checkout session initiated! (Ref: ${res.tx_ref || res.internal_reference}). Redirecting to payment portal...`);
          setPaymentModalOpen(false);
          window.location.href = res.checkout_url;
          return;
        } else {
          setSuccessMsg(`Chapa payment initiated successfully! Internal Ref: ${res.internal_reference || res.tx_ref}.`);
        }
      } else if (paymentMethodChoice === 'BANK_TRANSFER') {
        if (!transferRef.trim()) {
          alert('Please enter your bank transfer reference number.');
          setLoading(false);
          return;
        }
        await api.submitBankTransfer(selectedObligationToPay.id, {
          transfer_reference: transferRef,
          notes: transferNotes
        });
        setSuccessMsg(`Bank transfer ${transferRef} submitted for treasurer reconciliation.`);
      }
      setPaymentModalOpen(false);
      loadDashboardData();
      if (activeTab === 'contributions') {
        const obs = await api.getMemberContributions();
        setContributions(obs || []);
      }
    } catch (err) {
      alert(err.message || 'Payment submission failed.');
    } finally {
      setLoading(false);
    }
  };

  // View Receipt Slip
  const handleViewReceipt = async (receiptId) => {
    try {
      const slip = await api.getMemberReceipt(receiptId);
      setActiveReceiptSlip(slip);
      setReceiptModalOpen(true);
    } catch (err) {
      alert(err.message || 'Failed to load electronic receipt.');
    }
  };

  // Submit Dispute
  const handleSubmitDispute = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      await api.createMemberDispute(disputeForm);
      setSuccessMsg('Dispute filed successfully. Assigned organizer notified.');
      setDisputeModalOpen(false);
      setDisputeForm({ group_id: '', category: 'PAYMENT_NOT_RECORDED', title: '', description: '' });
      loadDashboardData();
      if (activeTab === 'disputes') {
        const disps = await api.getMemberDisputes();
        setDisputes(disps || []);
      }
    } catch (err) {
      alert(err.message || 'Dispute filing failed.');
    } finally {
      setLoading(false);
    }
  };

  // Accept / Decline Invitation
  const handleInvitationAction = async (invitationId, action) => {
    try {
      if (action === 'accept') {
        await api.acceptMemberInvitation(invitationId);
        setSuccessMsg('Invitation accepted! You have joined the Equb.');
      } else {
        await api.declineMemberInvitation(invitationId);
        setSuccessMsg('Invitation declined.');
      }
      const invs = await api.getMemberInvitations();
      setInvitations(invs || []);
      loadDashboardData();
    } catch (err) {
      alert(err.message || 'Action failed.');
    }
  };

  // Format ETB
  const formatETB = (val) => {
    const num = parseFloat(val || 0);
    return `ETB ${num.toLocaleString('en-US')}`;
  };

  const displayName = dashboardData?.member_name || user?.full_name || 'Dawit';
  const kpis = dashboardData?.kpis || {
    joined_groups_count: 2,
    confirmed_contributions_etb: '10000.00',
    outstanding_contributions_etb: '5000.00',
    next_contribution_date: 'Jun 30',
    upcoming_payout_etb: '15000.00'
  };

  return (
    <div className="member-portal-container" data-theme={effectiveTheme}>
      {/* ====================================================================
          DESKTOP SIDEBAR (Dark Slate #0f172a matching mockup)
          ==================================================================== */}
      <aside className="member-sidebar">
        {/* Brand Header */}
        <div className="member-sidebar-header">
          <div className="member-brand-emblem">
            <Wallet size={22} />
          </div>
          <div className="member-brand-title-wrap">
            <div className="member-brand-title">Digital Equb</div>
            <div className="member-brand-sub">Ethiopia</div>
          </div>
        </div>

        {/* Navigation List */}
        <nav className="member-nav-list">
          <button
            type="button"
            className={`member-nav-item ${activeTab === 'home' ? 'active' : ''}`}
            onClick={() => setActiveTab('home')}
          >
            <div className="member-nav-link-content">
              <Home size={18} />
              <span>{t('memNavHome') || 'Home'}</span>
            </div>
          </button>

          <button
            type="button"
            className={`member-nav-item ${activeTab === 'groups' || activeTab === 'group-detail' ? 'active' : ''}`}
            onClick={() => setActiveTab('groups')}
          >
            <div className="member-nav-link-content">
              <Users size={18} />
              <span>{t('memNavMyGroups') || 'My Groups'}</span>
            </div>
          </button>

          <button
            type="button"
            className={`member-nav-item ${activeTab === 'contributions' ? 'active' : ''}`}
            onClick={() => setActiveTab('contributions')}
          >
            <div className="member-nav-link-content">
              <Wallet size={18} />
              <span>{t('memNavContributions') || 'Contributions'}</span>
            </div>
          </button>

          <button
            type="button"
            className={`member-nav-item ${activeTab === 'payments' ? 'active' : ''}`}
            onClick={() => setActiveTab('payments')}
          >
            <div className="member-nav-link-content">
              <Clock size={18} />
              <span>{t('memNavPaymentHistory') || 'Payment History'}</span>
            </div>
          </button>

          <button
            type="button"
            className={`member-nav-item ${activeTab === 'payouts' ? 'active' : ''}`}
            onClick={() => setActiveTab('payouts')}
          >
            <div className="member-nav-link-content">
              <Gift size={18} />
              <span>{t('memNavPayoutSchedule') || 'Payout Schedule'}</span>
            </div>
          </button>

          <button
            type="button"
            className={`member-nav-item ${activeTab === 'announcements' ? 'active' : ''}`}
            onClick={() => setActiveTab('announcements')}
          >
            <div className="member-nav-link-content">
              <Megaphone size={18} />
              <span>{t('memNavAnnouncements') || 'Announcements'}</span>
            </div>
          </button>

          <button
            type="button"
            className={`member-nav-item ${activeTab === 'disputes' ? 'active' : ''}`}
            onClick={() => setActiveTab('disputes')}
          >
            <div className="member-nav-link-content">
              <MessageSquare size={18} />
              <span>{t('memNavDisputes') || 'Disputes'}</span>
            </div>
            {dashboardData?.badges?.active_disputes > 0 && (
              <span className="member-badge-count">{dashboardData.badges.active_disputes}</span>
            )}
          </button>

          <button
            type="button"
            className={`member-nav-item ${activeTab === 'notifications' ? 'active' : ''}`}
            onClick={() => setActiveTab('notifications')}
          >
            <div className="member-nav-link-content">
              <Bell size={18} />
              <span>{t('memNavNotifications') || 'Notifications'}</span>
            </div>
            {dashboardData?.badges?.unread_notifications > 0 && (
              <span className="member-badge-count">{dashboardData.badges.unread_notifications}</span>
            )}
          </button>

          <button
            type="button"
            className={`member-nav-item ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            <div className="member-nav-link-content">
              <Settings size={18} />
              <span>{t('memNavProfileSettings') || 'Profile & Settings'}</span>
            </div>
          </button>

          <button
            type="button"
            className={`member-nav-item ${activeTab === 'help' ? 'active' : ''}`}
            onClick={() => setActiveTab('help')}
          >
            <div className="member-nav-link-content">
              <Headphones size={18} />
              <span>{t('memNavHelpSupport') || 'Help & Support'}</span>
            </div>
          </button>
        </nav>

        {/* Bottom Promo Card (Together We Grow) */}
        <div className="member-sidebar-promo">
          <div className="member-promo-title">
            <span>🤝</span> {t('memTogetherWeGrow') || 'Together We Grow'}
          </div>
          <div className="member-promo-subtitle">
            Digital Equb Ethiopia — {t('memBrandSub') || 'Save, Share, Prosper'}
          </div>
        </div>
      </aside>

      {/* ====================================================================
          MAIN CONTENT AREA
          ==================================================================== */}
      <div className="member-main">
        {/* Topbar */}
        <header className="member-topbar">
          {/* Search Bar */}
          <div className="member-search-box">
            <Search size={18} color="#94a3b8" />
            <input
              type="text"
              className="member-search-input"
              placeholder={t('search') || 'Search groups, transactions...'}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Right Topbar Actions */}
          <div className="member-topbar-actions">
            {/* Sync Refresh Button */}
            <button
              type="button"
              className="btn-member-outline"
              onClick={handleRefreshAll}
              disabled={refreshing}
              title="Refresh member data"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.45rem 0.75rem',
                borderRadius: '8px',
                fontSize: '0.82rem',
                fontWeight: 600
              }}
            >
              <RefreshCw size={14} className={refreshing ? 'spin-animation' : ''} />
              <span>{refreshing ? 'Syncing...' : 'Refresh'}</span>
            </button>

            {/* Real Notification Center */}
            <NotificationCenter />

            {/* Theme & 4-Language Dropdowns */}
            <HeaderControls />

            {/* User Profile */}
            <div className="member-user-profile" onClick={() => setActiveTab('profile')}>
              <div className="member-avatar" style={{ overflow: 'hidden' }}>
                {user?.avatar ? (
                  <img src={user.avatar} alt="Avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  displayName.charAt(0).toUpperCase()
                )}
              </div>
              <div className="member-user-info">
                <span className="member-user-name">{displayName}</span>
                <span className="member-user-role">{t('roleMember') || 'Member'}</span>
              </div>
            </div>

            {/* Logout Button */}
            <button
              type="button"
              onClick={logout}
              className="btn-member-outline"
              style={{ padding: '0.4rem 0.75rem', borderRadius: '8px' }}
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>

        {/* Animated Movable Alert Notifications */}
        {errorMsg && (
          <ToastNotification
            message={errorMsg}
            type="error"
            onClose={() => setErrorMsg('')}
          />
        )}
        {successMsg && (
          <ToastNotification
            message={successMsg}
            type="success"
            onClose={() => setSuccessMsg('')}
          />
        )}

        {/* Content Body */}
        <main className="member-content">
          {/* =================================================================
              TAB 1: HOME (Matching Mockup media_1793636773508.png)
              ================================================================= */}
          {activeTab === 'home' && (
            <>
              {/* Hero Panoramic Greeting Banner */}
              <div className="member-hero-banner">
                <div>
                  <h1 className="member-hero-title">
                    Hello, {displayName}! 👋
                  </h1>
                  <p className="member-hero-sub">
                    {t('memHelloSub') || 'Your Equb participation at a glance.'}
                  </p>
                </div>
              </div>

              {/* 5 Top KPI Cards */}
              <div className="member-kpi-grid">
                {/* 1. Joined Groups */}
                <div className="member-kpi-card" onClick={() => setActiveTab('groups')} style={{ cursor: 'pointer' }}>
                  <div className="member-kpi-icon-box" style={{ background: '#dbeafe', color: '#2563eb' }}>
                    <Users size={24} />
                  </div>
                  <div className="member-kpi-info">
                    <div className="member-kpi-value">{kpis.joined_groups_count}</div>
                    <div className="member-kpi-label">{t('memJoinedGroups') || 'Joined Groups'}</div>
                  </div>
                </div>

                {/* 2. Confirmed Contributions */}
                <div className="member-kpi-card" onClick={() => setActiveTab('payments')} style={{ cursor: 'pointer' }}>
                  <div className="member-kpi-icon-box" style={{ background: '#dcfce7', color: '#10b981' }}>
                    <Wallet size={24} />
                  </div>
                  <div className="member-kpi-info">
                    <div className="member-kpi-value">{formatETB(kpis.confirmed_contributions_etb)}</div>
                    <div className="member-kpi-label">{t('memConfirmedContributions') || 'Confirmed Contributions'}</div>
                  </div>
                </div>

                {/* 3. Outstanding Contributions */}
                <div className="member-kpi-card" onClick={() => setActiveTab('contributions')} style={{ cursor: 'pointer' }}>
                  <div className="member-kpi-icon-box" style={{ background: '#ffedd5', color: '#f97316' }}>
                    <Clock size={24} />
                  </div>
                  <div className="member-kpi-info">
                    <div className="member-kpi-value">{formatETB(kpis.outstanding_contributions_etb)}</div>
                    <div className="member-kpi-label">{t('memOutstandingContributions') || 'Outstanding Contributions'}</div>
                  </div>
                </div>

                {/* 4. Next Contribution */}
                <div className="member-kpi-card" onClick={() => setActiveTab('contributions')} style={{ cursor: 'pointer' }}>
                  <div className="member-kpi-icon-box" style={{ background: '#f5f3ff', color: '#8b5cf6' }}>
                    <Calendar size={24} />
                  </div>
                  <div className="member-kpi-info">
                    <div className="member-kpi-value">{kpis.next_contribution_date}</div>
                    <div className="member-kpi-label">{t('memNextContribution') || 'Next Contribution'}</div>
                  </div>
                </div>

                {/* 5. Upcoming Payout */}
                <div className="member-kpi-card" onClick={() => setActiveTab('payouts')} style={{ cursor: 'pointer' }}>
                  <div className="member-kpi-icon-box" style={{ background: '#ecfdf5', color: '#059669' }}>
                    <Gift size={24} />
                  </div>
                  <div className="member-kpi-info">
                    <div className="member-kpi-value">{formatETB(kpis.upcoming_payout_etb)}</div>
                    <div className="member-kpi-label">{t('memUpcomingPayout') || 'Upcoming Payout'}</div>
                  </div>
                </div>
              </div>

              {/* Middle Row: My Groups + Upcoming Reminders */}
              <div className="member-dual-section">
                {/* Left Column: My Groups */}
                <div className="member-section-card">
                  <div className="member-section-header">
                    <div className="member-section-title">
                      <Users size={20} color="#2563eb" />
                      <span>{t('memMyGroups') || 'My Groups'}</span>
                    </div>
                    <button
                      type="button"
                      className="member-view-all-link"
                      onClick={() => setActiveTab('groups')}
                    >
                      <span>{t('memViewAllGroups') || 'View All Groups'}</span>
                      <ChevronRight size={16} />
                    </button>
                  </div>

                  <div className="member-groups-grid">
                    {(dashboardData?.my_groups || []).length === 0 ? (
                      <div style={{ padding: '2.5rem 1rem', textAlign: 'center', color: '#64748b', width: '100%' }}>
                        <Users size={36} color="#94a3b8" style={{ marginBottom: '0.5rem' }} />
                        <div style={{ fontWeight: 600, color: '#334155' }}>No Active Equb Groups</div>
                        <div style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>You have not joined any Equb groups yet. Check your invitations tab or contact your organizer.</div>
                      </div>
                    ) : (
                      (dashboardData?.my_groups || []).map((grp) => (
                        <div key={grp.id} className="member-group-item-card">
                          <div className="member-group-card-top">
                            <div className="member-group-thumb">
                              {grp.image_type === 'building' ? '🏢' : '🤝'}
                            </div>
                            <div className="member-group-card-header">
                              <div className="member-group-name">
                                <span>{grp.name}</span>
                                <span className="member-status-pill">{grp.status}</span>
                              </div>
                              <div className="member-group-specs">
                                <div className="member-group-spec-item">
                                  <Users size={14} />
                                  <span>{grp.members_count} Members</span>
                                </div>
                                <div className="member-group-spec-item">
                                  <DollarSign size={14} />
                                  <span>{formatETB(grp.contribution_amount)} / {grp.contribution_frequency}</span>
                                </div>
                                <div className="member-group-spec-item">
                                  <Calendar size={14} />
                                  <span>Next Due: {grp.next_due_date}</span>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Progress Bar */}
                          <div className="member-progress-block">
                            <div className="member-progress-header">
                              <span>{t('memYourProgress') || 'Your Progress'}</span>
                              <span>{grp.progress_percent}%</span>
                            </div>
                            <div className="member-progress-bar">
                              <div
                                className="member-progress-fill"
                                style={{
                                  width: `${grp.progress_percent}%`,
                                  backgroundColor: grp.image_type === 'building' ? '#10b981' : '#2563eb'
                                }}
                              />
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="member-group-card-actions">
                            <button
                              type="button"
                              className="btn-member-primary"
                              onClick={() => handleOpenGroupDetail(grp.id)}
                            >
                              <Eye size={16} />
                              <span>{t('memViewDetails') || 'View Details'}</span>
                            </button>
                            <button
                              type="button"
                              className="btn-member-outline"
                              onClick={() => handleOpenRules(grp)}
                            >
                              <FileText size={16} />
                              <span>{t('memViewRules') || 'View Rules'}</span>
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Right Column: Upcoming Reminders */}
                <div className="member-section-card">
                  <div className="member-section-header">
                    <div className="member-section-title">
                      <Calendar size={20} color="#2563eb" />
                      <span>{t('memUpcomingReminders') || 'Upcoming Reminders'}</span>
                    </div>
                    <button
                      type="button"
                      className="member-view-all-link"
                      onClick={() => setActiveTab('contributions')}
                    >
                      <span>View All</span>
                      <ChevronRight size={16} />
                    </button>
                  </div>

                  <div className="member-reminders-list">
                    {(dashboardData?.upcoming_reminders || []).length === 0 ? (
                      <div style={{ padding: '2rem 1rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.85rem' }}>
                        <CheckCircle size={24} color="#10b981" style={{ marginBottom: '0.35rem', display: 'inline-block' }} />
                        <div>No upcoming reminders. All contributions are up to date.</div>
                      </div>
                    ) : (
                      (dashboardData?.upcoming_reminders || []).map((rem) => (
                        <div key={rem.id} className="member-reminder-item">
                          <div className="member-reminder-left">
                            <div
                              className="member-reminder-icon"
                              style={{
                                background: rem.badge_color === 'pink' ? '#fee2e2' : rem.badge_color === 'blue' ? '#dbeafe' : '#ffedd5',
                                color: rem.badge_color === 'pink' ? '#ef4444' : rem.badge_color === 'blue' ? '#2563eb' : '#f97316'
                              }}
                            >
                              {rem.icon_type === 'pie_chart' ? <Clock size={18} /> : rem.icon_type === 'gift' ? <Gift size={18} /> : <Users size={18} />}
                            </div>
                            <div>
                              <div className="member-reminder-title">{rem.title}</div>
                              <div className="member-reminder-sub">{rem.subtitle}</div>
                            </div>
                          </div>
                          <span className={`member-date-badge ${rem.badge_color}`}>
                            {rem.badge}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Bottom Row: Recent Activity + Quick Actions */}
              <div className="member-dual-section">
                {/* Left Column: Recent Activity */}
                <div className="member-section-card">
                  <div className="member-section-header">
                    <div className="member-section-title">
                      <span>⚡</span>
                      <span>{t('memRecentActivity') || 'Recent Activity'}</span>
                    </div>
                    <button
                      type="button"
                      className="member-view-all-link"
                      onClick={() => setActiveTab('payments')}
                    >
                      <span>View All</span>
                      <ChevronRight size={16} />
                    </button>
                  </div>

                  <div className="member-activity-list">
                    {(dashboardData?.recent_activity || []).length === 0 ? (
                      <div style={{ padding: '2rem 1rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.85rem' }}>
                        <div>No recent activity recorded yet.</div>
                      </div>
                    ) : (
                      (dashboardData?.recent_activity || []).map((act) => (
                        <div key={act.id} className="member-activity-item">
                          <div className="member-activity-left">
                            <div
                              className="member-activity-icon"
                              style={{
                                background:
                                  act.icon_color === 'green' ? '#dcfce7' :
                                  act.icon_color === 'blue' ? '#dbeafe' :
                                  act.icon_color === 'purple' ? '#f5f3ff' :
                                  act.icon_color === 'amber' ? '#fef3c7' : '#cffafe',
                                color:
                                  act.icon_color === 'green' ? '#10b981' :
                                  act.icon_color === 'blue' ? '#2563eb' :
                                  act.icon_color === 'purple' ? '#8b5cf6' :
                                  act.icon_color === 'amber' ? '#f59e0b' : '#06b6d4'
                              }}
                            >
                              {act.icon === 'check' && <Check size={16} />}
                              {act.icon === 'users' && <Users size={16} />}
                              {act.icon === 'megaphone' && <Megaphone size={16} />}
                              {act.icon === 'trophy' && <Gift size={16} />}
                              {act.icon === 'message' && <MessageSquare size={16} />}
                            </div>
                            <span className="member-activity-text">{act.title}</span>
                          </div>
                          <span className="member-activity-time">{act.time_ago}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Right Column: Quick Actions Grid (6 cards matching mockup) */}
                <div className="member-section-card">
                  <div className="member-section-header">
                    <div className="member-section-title">
                      <span>⚡</span>
                      <span>{t('memQuickActions') || 'Quick Actions'}</span>
                    </div>
                  </div>

                  <div className="member-quick-actions-grid">
                    {/* 1. Make Payment */}
                    <div
                      className="member-quick-action-card blue"
                      onClick={() => {
                        const firstPending = (contributions || []).find(c => c.status !== 'PAID');
                        if (firstPending) {
                          handleInitiatePayment(firstPending);
                        } else {
                          setActiveTab('contributions');
                        }
                      }}
                    >
                      <div className="member-action-icon-circle" style={{ background: '#dbeafe', color: '#2563eb' }}>
                        <CreditCard size={20} />
                      </div>
                      <div className="member-action-title">{t('memMakePayment') || 'Make Payment'}</div>
                    </div>

                    {/* 2. View Contributions */}
                    <div className="member-quick-action-card green" onClick={() => setActiveTab('contributions')}>
                      <div className="member-action-icon-circle" style={{ background: '#dcfce7', color: '#10b981' }}>
                        <Users size={20} />
                      </div>
                      <div className="member-action-title">{t('memViewContributions') || 'View Contributions'}</div>
                    </div>

                    {/* 3. View Payout Schedule */}
                    <div className="member-quick-action-card purple" onClick={() => setActiveTab('payouts')}>
                      <div className="member-action-icon-circle" style={{ background: '#f5f3ff', color: '#8b5cf6' }}>
                        <Calendar size={20} />
                      </div>
                      <div className="member-action-title">{t('memViewPayoutSchedule') || 'View Payout Schedule'}</div>
                    </div>

                    {/* 4. Submit Dispute */}
                    <div className="member-quick-action-card orange" onClick={() => setDisputeModalOpen(true)}>
                      <div className="member-action-icon-circle" style={{ background: '#ffedd5', color: '#f97316' }}>
                        <FileText size={20} />
                      </div>
                      <div className="member-action-title">{t('memSubmitDispute') || 'Submit Dispute'}</div>
                    </div>

                    {/* 5. Manage Notifications */}
                    <div className="member-quick-action-card teal" onClick={() => setActiveTab('notifications')}>
                      <div className="member-action-icon-circle" style={{ background: '#ccfbf1', color: '#0d9488' }}>
                        <Bell size={20} />
                      </div>
                      <div className="member-action-title">{t('memManageNotifications') || 'Manage Notifications'}</div>
                    </div>

                    {/* 6. Update Profile */}
                    <div className="member-quick-action-card slate" onClick={() => setActiveTab('profile')}>
                      <div className="member-action-icon-circle" style={{ background: '#f1f5f9', color: '#475569' }}>
                        <Settings size={20} />
                      </div>
                      <div className="member-action-title">{t('memUpdateProfile') || 'Update Profile'}</div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* =================================================================
              TAB 2: MY GROUPS LIST & INVITATIONS
              ================================================================= */}
          {activeTab === 'groups' && (
            <div className="member-section-card">
              <div className="member-section-header">
                <div className="member-section-title">
                  <Users size={22} color="#2563eb" />
                  <span>My Enrolled Equb Groups</span>
                </div>
              </div>

              {/* Pending Invitations Banner */}
              {invitations.length > 0 && (
                <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '12px', padding: '1rem', marginBottom: '1rem' }}>
                  <div style={{ fontWeight: 700, color: '#1e3a8a', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <Bell size={18} />
                    <span>You have {invitations.length} pending Equb invitation(s)</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {invitations.map((inv) => (
                      <div key={inv.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#fff', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                        <div>
                          <div style={{ fontWeight: 600 }}>{inv.group.name}</div>
                          <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                            {formatETB(inv.group.contribution_amount)} / {inv.group.contribution_frequency} • Organizer: {inv.group.organizer_name}
                          </div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            type="button"
                            className="btn-member-primary"
                            style={{ padding: '0.4rem 0.8rem' }}
                            onClick={() => handleInvitationAction(inv.id, 'accept')}
                          >
                            Accept & Join
                          </button>
                          <button
                            type="button"
                            className="btn-member-outline"
                            style={{ padding: '0.4rem 0.8rem' }}
                            onClick={() => handleInvitationAction(inv.id, 'decline')}
                          >
                            Decline
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Groups List */}
              <div className="member-groups-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
                {groupsList.map((item) => {
                  const g = item.group;
                  return (
                    <div key={item.membership_id} className="member-group-item-card">
                      <div className="member-group-card-top">
                        <div className="member-group-thumb">🏢</div>
                        <div className="member-group-card-header">
                          <div className="member-group-name">
                            <span>{g.name}</span>
                            <span className="member-status-pill">{item.membership_status}</span>
                          </div>
                          <div className="member-group-specs">
                            <div className="member-group-spec-item">
                              <Users size={14} />
                              <span>{g.active_members_count} / {g.capacity} Members</span>
                            </div>
                            <div className="member-group-spec-item">
                              <DollarSign size={14} />
                              <span>{formatETB(g.contribution_amount)} / {g.frequency_display}</span>
                            </div>
                            <div className="member-group-spec-item">
                              <Calendar size={14} />
                              <span>Next Due: {g.next_due_date || 'N/A'}</span>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="member-progress-block">
                        <div className="member-progress-header">
                          <span>Group Collection Progress</span>
                          <span>{g.progress_percent}%</span>
                        </div>
                        <div className="member-progress-bar">
                          <div className="member-progress-fill" style={{ width: `${g.progress_percent}%`, backgroundColor: '#2563eb' }} />
                        </div>
                      </div>

                      <div className="member-group-card-actions">
                        <button type="button" className="btn-member-primary" onClick={() => handleOpenGroupDetail(g.id)}>
                          <Eye size={16} />
                          <span>View Group Details</span>
                        </button>
                        <button type="button" className="btn-member-outline" onClick={() => handleOpenRules(g)}>
                          <FileText size={16} />
                          <span>Rules</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* =================================================================
              TAB 3: GROUP DETAIL WORKSPACE (8 Tabs)
              ================================================================= */}
          {activeTab === 'group-detail' && selectedGroupDetail && (
            <div className="member-section-card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #e2e8f0', paddingBottom: '1rem' }}>
                <div>
                  <button
                    type="button"
                    onClick={() => setActiveTab('groups')}
                    style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', fontSize: '0.85rem', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.2rem' }}
                  >
                    ← Back to Groups
                  </button>
                  <h2 style={{ fontSize: '1.4rem', fontWeight: 800, margin: 0 }}>{selectedGroupDetail.group.name}</h2>
                  <div style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.2rem' }}>
                    {selectedGroupDetail.group.group_purpose} • Organizer: {selectedGroupDetail.group.organizer_name}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#2563eb' }}>
                    {formatETB(selectedGroupDetail.group.contribution_amount)}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#64748b' }}>per {selectedGroupDetail.group.contribution_frequency}</div>
                </div>
              </div>

              {/* Sub-tabs */}
              <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #e2e8f0', overflowX: 'auto', paddingBottom: '0.5rem' }}>
                {['overview', 'rules', 'schedule', 'payments', 'payouts', 'members', 'destinations', 'disputes'].map(tabKey => (
                  <button
                    key={tabKey}
                    type="button"
                    onClick={() => setGroupDetailTab(tabKey)}
                    style={{
                      padding: '0.5rem 0.85rem',
                      borderRadius: '8px',
                      border: 'none',
                      background: groupDetailTab === tabKey ? '#2563eb' : 'transparent',
                      color: groupDetailTab === tabKey ? '#fff' : '#64748b',
                      fontWeight: groupDetailTab === tabKey ? 700 : 500,
                      cursor: 'pointer',
                      fontSize: '0.85rem',
                      textTransform: 'capitalize'
                    }}
                  >
                    {tabKey}
                  </button>
                ))}
              </div>

              {/* Sub-tab 1: Overview */}
              {groupDetailTab === 'overview' && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '1rem' }}>
                  <div style={{ border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1.25rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.75rem' }}>Group Parameters</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem' }}>
                      <div><strong>Status:</strong> {selectedGroupDetail.group.status}</div>
                      <div><strong>Verification:</strong> {selectedGroupDetail.group.verification_status}</div>
                      <div><strong>Payout Method:</strong> {selectedGroupDetail.group.payout_method}</div>
                      <div><strong>Capacity:</strong> {selectedGroupDetail.group.capacity} members</div>
                      <div><strong>Start Date:</strong> {selectedGroupDetail.group.start_date}</div>
                    </div>
                  </div>
                  <div style={{ border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1.25rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.75rem' }}>Your Participation</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem' }}>
                      <div><strong>Membership Status:</strong> {selectedGroupDetail.my_membership.status}</div>
                      <div><strong>Rotation Order Position:</strong> Round #{selectedGroupDetail.my_membership.payout_order_index || 'TBD'}</div>
                      <div><strong>Enrolled Since:</strong> {selectedGroupDetail.my_membership.joined_at}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Sub-tab 2: Rules */}
              {groupDetailTab === 'rules' && (
                <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {selectedGroupDetail.rules.map(r => (
                    <div key={r.id} style={{ border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1.25rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h4 style={{ margin: 0, fontWeight: 700 }}>Version {r.version_number}: {r.title}</h4>
                        {r.is_active && <span className="member-status-pill">Active Rules</span>}
                      </div>
                      <p style={{ marginTop: '0.75rem', fontSize: '0.9rem', color: '#334155', lineHeight: 1.5 }}>{r.terms_text}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Sub-tab 3: Schedule */}
              {groupDetailTab === 'schedule' && (
                <div style={{ marginTop: '1rem' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#64748b' }}>
                        <th style={{ padding: '0.75rem' }}>Round</th>
                        <th style={{ padding: '0.75rem' }}>Due Date</th>
                        <th style={{ padding: '0.75rem' }}>Expected</th>
                        <th style={{ padding: '0.75rem' }}>Paid</th>
                        <th style={{ padding: '0.75rem' }}>Status</th>
                        <th style={{ padding: '0.75rem' }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedGroupDetail.obligations.map(ob => (
                        <tr key={ob.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '0.75rem', fontWeight: 600 }}>Round {ob.period_number}</td>
                          <td style={{ padding: '0.75rem' }}>{ob.due_date}</td>
                          <td style={{ padding: '0.75rem', fontWeight: 600 }}>{formatETB(ob.expected_amount)}</td>
                          <td style={{ padding: '0.75rem', color: '#10b981', fontWeight: 600 }}>{formatETB(ob.amount_paid)}</td>
                          <td style={{ padding: '0.75rem' }}>
                            <span className="member-status-pill" style={{ background: ob.status === 'PAID' ? '#dcfce7' : '#fee2e2', color: ob.status === 'PAID' ? '#15803d' : '#b91c1c' }}>
                              {ob.status}
                            </span>
                          </td>
                          <td style={{ padding: '0.75rem' }}>
                            {ob.status !== 'PAID' && (
                              <button
                                type="button"
                                className="btn-member-primary"
                                style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem' }}
                                onClick={() => handleInitiatePayment(ob)}
                              >
                                Pay Now
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Sub-tab 4: My Payments */}
              {groupDetailTab === 'payments' && (
                <div style={{ marginTop: '1rem' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#64748b' }}>
                        <th style={{ padding: '0.75rem' }}>Receipt #</th>
                        <th style={{ padding: '0.75rem' }}>Method</th>
                        <th style={{ padding: '0.75rem' }}>Amount</th>
                        <th style={{ padding: '0.75rem' }}>Date</th>
                        <th style={{ padding: '0.75rem' }}>Status</th>
                        <th style={{ padding: '0.75rem' }}>Receipt</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedGroupDetail.payments.map(p => (
                        <tr key={p.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '0.75rem', fontWeight: 700 }}>{p.receipt_number}</td>
                          <td style={{ padding: '0.75rem' }}>{p.payment_method_display}</td>
                          <td style={{ padding: '0.75rem', fontWeight: 700 }}>{formatETB(p.amount)}</td>
                          <td style={{ padding: '0.75rem' }}>{p.created_at}</td>
                          <td style={{ padding: '0.75rem' }}>
                            <span className="member-status-pill" style={{ background: p.status === 'CONFIRMED' ? '#dcfce7' : '#fef3c7', color: p.status === 'CONFIRMED' ? '#15803d' : '#b45309' }}>
                              {p.status}
                            </span>
                          </td>
                          <td style={{ padding: '0.75rem' }}>
                            <button
                              type="button"
                              className="btn-member-outline"
                              style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}
                              onClick={() => handleViewReceipt(p.id)}
                            >
                              <Printer size={14} /> Slip
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Sub-tab 5: Sanitized Member Roster (No Private Data) */}
              {groupDetailTab === 'members' && (
                <div style={{ marginTop: '1rem' }}>
                  <div style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '0.75rem' }}>
                    <Info size={14} style={{ display: 'inline', marginRight: '4px' }} />
                    Member privacy protected: Contact numbers and private payment records of other members are hidden.
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '1rem' }}>
                    {selectedGroupDetail.sanitized_members.map(m => (
                      <div key={m.id} style={{ border: '1px solid #e2e8f0', borderRadius: '10px', padding: '0.85rem', background: m.is_you ? '#eff6ff' : '#fff' }}>
                        <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span>{m.name}</span>
                          {m.is_you && <span style={{ fontSize: '0.7rem', background: '#2563eb', color: '#fff', padding: '0.1rem 0.4rem', borderRadius: '4px' }}>You</span>}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem' }}>
                          Rotation Order: #{m.payout_order_index || 'TBD'} • Joined: {m.joined_at}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Sub-tab 6: Bank Destinations */}
              {groupDetailTab === 'destinations' && (
                <div style={{ marginTop: '1rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
                  {selectedGroupDetail.destinations.map(d => (
                    <div key={d.id} style={{ border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1.25rem', background: '#f8fafc' }}>
                      <div style={{ fontWeight: 700, fontSize: '1rem', color: '#1e3a8a' }}>{d.provider_or_bank}</div>
                      <div style={{ marginTop: '0.5rem', fontSize: '0.88rem' }}>
                        <div><strong>Account Name:</strong> {d.account_name}</div>
                        <div><strong>Account Number:</strong> <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{d.account_number}</span></div>
                        {d.branch_or_details && <div><strong>Branch:</strong> {d.branch_or_details}</div>}
                      </div>
                      {d.transfer_instructions && (
                        <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', background: '#fff', padding: '0.5rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                          {d.transfer_instructions}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* =================================================================
              TAB 4: CONTRIBUTIONS & OBLIGATIONS
              ================================================================= */}
          {activeTab === 'contributions' && (
            <div className="member-section-card">
              <div className="member-section-header">
                <div className="member-section-title">
                  <Wallet size={22} color="#2563eb" />
                  <span>Personal Contribution Obligations</span>
                </div>
                {/* Filter Pills */}
                <div style={{ display: 'flex', gap: '0.4rem' }}>
                  {['ALL', 'PENDING', 'PAID', 'OVERDUE'].map(st => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => setContributionFilter(st)}
                      style={{
                        padding: '0.35rem 0.75rem',
                        borderRadius: '9999px',
                        border: '1px solid var(--mem-border)',
                        background: contributionFilter === st ? '#2563eb' : '#fff',
                        color: contributionFilter === st ? '#fff' : '#64748b',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        cursor: 'pointer'
                      }}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>

              {/* Table */}
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#64748b' }}>
                      <th style={{ padding: '0.75rem' }}>Group</th>
                      <th style={{ padding: '0.75rem' }}>Period</th>
                      <th style={{ padding: '0.75rem' }}>Due Date</th>
                      <th style={{ padding: '0.75rem' }}>Expected</th>
                      <th style={{ padding: '0.75rem' }}>Paid</th>
                      <th style={{ padding: '0.75rem' }}>Status</th>
                      <th style={{ padding: '0.75rem' }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {contributions
                      .filter(c => contributionFilter === 'ALL' || c.status === contributionFilter)
                      .map((ob) => (
                        <tr key={ob.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                          <td style={{ padding: '0.75rem', fontWeight: 600 }}>{ob.group_name}</td>
                          <td style={{ padding: '0.75rem' }}>Round {ob.period_number}</td>
                          <td style={{ padding: '0.75rem' }}>{ob.due_date}</td>
                          <td style={{ padding: '0.75rem', fontWeight: 700 }}>{formatETB(ob.expected_amount)}</td>
                          <td style={{ padding: '0.75rem', color: '#10b981', fontWeight: 700 }}>{formatETB(ob.amount_paid)}</td>
                          <td style={{ padding: '0.75rem' }}>
                            <span className="member-status-pill" style={{
                              background: ob.status === 'PAID' ? '#dcfce7' : ob.status === 'OVERDUE' ? '#fee2e2' : '#ffedd5',
                              color: ob.status === 'PAID' ? '#15803d' : ob.status === 'OVERDUE' ? '#b91c1c' : '#c2410c'
                            }}>
                              {ob.status_display}
                            </span>
                          </td>
                          <td style={{ padding: '0.75rem' }}>
                            {ob.status !== 'PAID' ? (
                              <button
                                type="button"
                                className="btn-member-primary"
                                style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                                onClick={() => handleInitiatePayment(ob)}
                              >
                                Pay Now
                              </button>
                            ) : (
                              <span style={{ color: '#10b981', fontSize: '0.85rem', fontWeight: 600 }}>✓ Settled</span>
                            )}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>



            </div>
          )}

          {/* =================================================================
              TAB 5: PAYMENT HISTORY & RECEIPTS
              ================================================================= */}
          {activeTab === 'payments' && (
            <div className="member-section-card">
              <div className="member-section-header">
                <div className="member-section-title">
                  <Clock size={22} color="#2563eb" />
                  <span>Personal Payment Receipts History</span>
                </div>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#64748b' }}>
                      <th style={{ padding: '0.75rem' }}>Receipt #</th>
                      <th style={{ padding: '0.75rem' }}>Group</th>
                      <th style={{ padding: '0.75rem' }}>Method</th>
                      <th style={{ padding: '0.75rem' }}>Amount</th>
                      <th style={{ padding: '0.75rem' }}>Date</th>
                      <th style={{ padding: '0.75rem' }}>Status</th>
                      <th style={{ padding: '0.75rem' }}>Official Slip</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map(p => (
                      <tr key={p.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '0.75rem', fontWeight: 700, fontFamily: 'monospace' }}>{p.receipt_number}</td>
                        <td style={{ padding: '0.75rem' }}>{p.group_name}</td>
                        <td style={{ padding: '0.75rem' }}>{p.payment_method_display}</td>
                        <td style={{ padding: '0.75rem', fontWeight: 700 }}>{formatETB(p.amount)}</td>
                        <td style={{ padding: '0.75rem' }}>{p.created_at}</td>
                        <td style={{ padding: '0.75rem' }}>
                          <span className="member-status-pill" style={{
                            background: p.status === 'CONFIRMED' ? '#dcfce7' : '#fef3c7',
                            color: p.status === 'CONFIRMED' ? '#15803d' : '#b45309'
                          }}>
                            {p.status_display}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <button
                            type="button"
                            className="btn-member-outline"
                            style={{ padding: '0.35rem 0.65rem', fontSize: '0.8rem' }}
                            onClick={() => handleViewReceipt(p.id)}
                          >
                            <Printer size={14} /> View Slip
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Proposed Payment Agreements (Option B) */}
              {memberAgreements.length > 0 && (
                <div className="member-section-card" style={{ border: '2px solid #93c5fd', background: '#f8fafc' }}>
                  <div className="member-section-header">
                    <div className="member-section-title">
                      <Clock size={22} color="#2563eb" />
                      <span>Formal Payment Agreements & Installment Plans (Option B)</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {memberAgreements.map((agr) => (
                      <div key={agr.id} style={{ background: '#ffffff', borderRadius: '10px', padding: '1.25rem', border: '1px solid #e2e8f0' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                          <div>
                            <div style={{ fontWeight: 800, fontSize: '1.1rem', color: '#0f172a' }}>
                              Equb Group: {agr.group_name || 'Your Equb Group'}
                            </div>
                            <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.2rem' }}>
                              Reason / Basis: "{agr.member_reason || 'Installment repayment arrangement'}"
                            </div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#dc2626' }}>
                              ETB {Number(agr.total_outstanding_amount || 0).toLocaleString()}
                            </div>
                            <span className={`member-status-pill ${agr.status === 'ACCEPTED' ? 'green' : 'orange'}`}>
                              {agr.status}
                            </span>
                          </div>
                        </div>

                        {/* Installments Table */}
                        <div style={{ marginTop: '1rem', borderTop: '1px solid #f1f5f9', paddingTop: '0.75rem' }}>
                          <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#475569', marginBottom: '0.4rem' }}>
                            Scheduled Installments:
                          </div>
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.5rem' }}>
                            {(agr.installments || []).map((inst) => (
                              <div key={inst.id} style={{ background: '#f8fafc', padding: '0.6rem 0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                                <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>#{inst.installment_number}: ETB {Number(inst.amount).toLocaleString()}</div>
                                <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Due: {inst.due_date}</div>
                                <div style={{ fontSize: '0.72rem', color: inst.status === 'PAID' ? '#16a34a' : '#d97706', fontWeight: 700, marginTop: '0.2rem' }}>
                                  {inst.status}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Action buttons if pending member acceptance */}
                        {agr.status === 'PENDING_MEMBER_ACCEPTANCE' && (
                          <div style={{ marginTop: '1rem', display: 'flex', gap: '0.75rem', justifyContent: 'flex-end', borderTop: '1px solid #f1f5f9', paddingTop: '0.75rem' }}>
                            <button
                              type="button"
                              className="btn-member-outline"
                              onClick={() => handleRespondAgreement(agr.id, false)}
                              disabled={respondingAgreementId === agr.id}
                              style={{ color: '#dc2626', borderColor: '#fca5a5' }}
                            >
                              Decline Agreement
                            </button>
                            <button
                              type="button"
                              className="btn-member-primary"
                              onClick={() => handleRespondAgreement(agr.id, true)}
                              disabled={respondingAgreementId === agr.id}
                              style={{ background: '#16a34a', borderColor: '#15803d', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
                            >
                              {respondingAgreementId === agr.id ? <RefreshCw size={14} className="spin-animation" /> : <CheckCircle2 size={16} />}
                              <span>Accept Payment Agreement</span>
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* =================================================================
              TAB 6: PAYOUT SCHEDULE
              ================================================================= */}
          {activeTab === 'payouts' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Personal Upcoming Payouts */}
              <div className="member-section-card">
                <div className="member-section-header">
                  <div className="member-section-title">
                    <Gift size={22} color="#10b981" />
                    <span>Your Scheduled Payouts</span>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
                  {(payoutSchedule.personal_payouts || []).map(po => (
                    <div key={po.id} style={{ border: '2px solid #bbf7d0', background: '#f0fdf4', borderRadius: '12px', padding: '1.25rem' }}>
                      <div style={{ fontWeight: 700, fontSize: '1.1rem', color: '#15803d' }}>{po.group_name}</div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, margin: '0.5rem 0', color: '#0f172a' }}>{formatETB(po.amount)}</div>
                      <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                        Round #{po.period_number} • Scheduled for {po.scheduled_date}
                      </div>
                      <div style={{ marginTop: '0.75rem' }}>
                        <span className="member-status-pill" style={{ background: '#dcfce7', color: '#15803d' }}>
                          {po.status_display}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Group Rotation Sequences */}
              <div className="member-section-card">
                <div className="member-section-header">
                  <div className="member-section-title">
                    <Calendar size={22} color="#2563eb" />
                    <span>Group Rotation Sequence Transparency</span>
                  </div>
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#64748b' }}>
                      <th style={{ padding: '0.75rem' }}>Group</th>
                      <th style={{ padding: '0.75rem' }}>Recipient</th>
                      <th style={{ padding: '0.75rem' }}>Amount</th>
                      <th style={{ padding: '0.75rem' }}>Scheduled Date</th>
                      <th style={{ padding: '0.75rem' }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(payoutSchedule.group_schedules || []).map(po => (
                      <tr key={po.id} style={{ borderBottom: '1px solid #f1f5f9', background: po.is_you ? '#eff6ff' : 'transparent' }}>
                        <td style={{ padding: '0.75rem', fontWeight: 600 }}>{po.group_name}</td>
                        <td style={{ padding: '0.75rem' }}>
                          {po.recipient_name} {po.is_you && <span style={{ fontSize: '0.7rem', background: '#2563eb', color: '#fff', padding: '0.1rem 0.35rem', borderRadius: '4px' }}>You</span>}
                        </td>
                        <td style={{ padding: '0.75rem', fontWeight: 700 }}>{formatETB(po.amount)}</td>
                        <td style={{ padding: '0.75rem' }}>{po.scheduled_date}</td>
                        <td style={{ padding: '0.75rem' }}>
                          <span className="member-status-pill">{po.status_display}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Digital Equb Lottery Integrity & SHA-256 Verifiable Proof */}
              <div className="member-section-card" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                <div className="member-section-header">
                  <div className="member-section-title">
                    <Trophy size={22} color="#f59e0b" />
                    <span>Cryptographic Lottery Verification & Transparency</span>
                  </div>
                </div>
                <div style={{ fontSize: '0.88rem', color: '#334155', lineHeight: 1.6 }}>
                  <p style={{ margin: '0 0 0.5rem 0' }}>
                    All Digital Equb lottery selections are generated using cryptographically strong pseudo-random number generators (CSPRNG) backed by the operating system kernel (<code>secrets.SystemRandom()</code>).
                  </p>
                  <p style={{ margin: 0, fontSize: '0.82rem', color: '#64748b' }}>
                    🛡️ <strong>Fair Play Guarantee:</strong> No organizer, treasurer, administrator, or developer can predict or manipulate draw winners. If active member payments are incomplete past the grace period, the lottery is automatically paused until resolved through authorized group consensus.
                  </p>
                </div>
              </div>

            </div>
          )}

          {/* =================================================================
              TAB 7: ANNOUNCEMENTS
              ================================================================= */}
          {activeTab === 'announcements' && (
            <div className="member-section-card">
              <div className="member-section-header">
                <div className="member-section-title">
                  <Megaphone size={22} color="#2563eb" />
                  <span>Platform & Group Notices</span>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {announcements.map(ann => (
                  <div key={ann.id} style={{ border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1.25rem', background: '#f8fafc' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>
                        {language === 'am' && ann.title_am ? ann.title_am : ann.title}
                      </h3>
                      <span style={{ fontSize: '0.8rem', color: '#64748b' }}>{ann.published_at}</span>
                    </div>
                    <p style={{ marginTop: '0.75rem', fontSize: '0.92rem', color: '#334155', lineHeight: 1.6 }}>
                      {language === 'am' && ann.content_am ? ann.content_am : ann.content}
                    </p>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.5rem' }}>
                      Published by: {ann.author}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* =================================================================
              TAB 8: DISPUTES WORKSPACE
              ================================================================= */}
          {activeTab === 'disputes' && (
            <div className="member-section-card">
              <div className="member-section-header">
                <div className="member-section-title">
                  <MessageSquare size={22} color="#f97316" />
                  <span>Disputes & Grievance Center</span>
                </div>
                <button
                  type="button"
                  className="btn-member-primary"
                  onClick={() => setDisputeModalOpen(true)}
                >
                  + File New Dispute
                </button>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #e2e8f0', color: '#64748b' }}>
                      <th style={{ padding: '0.75rem' }}>Date</th>
                      <th style={{ padding: '0.75rem' }}>Group</th>
                      <th style={{ padding: '0.75rem' }}>Subject</th>
                      <th style={{ padding: '0.75rem' }}>Category</th>
                      <th style={{ padding: '0.75rem' }}>Status</th>
                      <th style={{ padding: '0.75rem' }}>Resolution Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {disputes.map(d => (
                      <tr key={d.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '0.75rem' }}>{d.created_at}</td>
                        <td style={{ padding: '0.75rem', fontWeight: 600 }}>{d.group_name}</td>
                        <td style={{ padding: '0.75rem', fontWeight: 700 }}>{d.title}</td>
                        <td style={{ padding: '0.75rem' }}>{d.category_display}</td>
                        <td style={{ padding: '0.75rem' }}>
                          <span className="member-status-pill" style={{ background: '#fef3c7', color: '#b45309' }}>
                            {d.status_display}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem', fontSize: '0.85rem', color: '#475569' }}>
                          {d.resolution_notes || 'Under review by organizer.'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>



            </div>
          )}

          {/* =================================================================
              TAB 9: NOTIFICATIONS
              ================================================================= */}
          {activeTab === 'notifications' && (
            <div className="member-section-card">
              <div className="member-section-header">
                <div className="member-section-title">
                  <Bell size={22} color="#2563eb" />
                  <span>Notification Center</span>
                </div>
                <button
                  type="button"
                  className="btn-member-outline"
                  onClick={async () => {
                    await api.markAllMemberNotificationsRead();
                    const notifs = await api.getMemberNotifications();
                    setNotifications(notifs || []);
                    loadDashboardData();
                  }}
                >
                  Mark All as Read
                </button>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {Array.isArray(notifications) && notifications.length > 0 ? (
                  notifications.map(n => (
                    <div
                      key={n.id}
                      style={{
                        border: '1px solid #e2e8f0',
                        borderRadius: '10px',
                        padding: '1rem',
                        background: n.is_read ? '#ffffff' : '#f0fdf4',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
                          {language === 'am' && n.title_am ? n.title_am : n.title}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#475569', marginTop: '0.2rem' }}>
                          {language === 'am' && n.message_am ? n.message_am : n.message}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.35rem' }}>
                          {n.created_at}
                        </div>
                      </div>
                      {!n.is_read && (
                        <button
                          type="button"
                          onClick={async () => {
                            await api.markMemberNotificationRead(n.id);
                            const notifs = await api.getMemberNotifications();
                            setNotifications(Array.isArray(notifs) ? notifs : (notifs?.results || []));
                            loadDashboardData();
                          }}
                          style={{ border: 'none', background: 'none', color: '#2563eb', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600 }}
                        >
                          Mark Read
                        </button>
                      )}
                    </div>
                  ))
                ) : (
                  <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b', fontSize: '0.88rem' }}>
                    No notifications at this time.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* =================================================================
              TAB 10: PROFILE & SETTINGS
              ================================================================= */}
          {activeTab === 'profile' && profileData && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
              {/* Profile Details */}
              <div className="member-section-card">
                <div className="member-section-header">
                  <div className="member-section-title">
                    <Settings size={22} color="#2563eb" />
                    <span>Member Profile Information</span>
                  </div>
                </div>
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    try {
                      const payload = {
                        full_name: (profileData.full_name || '').trim(),
                        phone_number: (profileData.phone_number || '').trim(),
                        preferred_language: profileData.preferred_language || 'en',
                        avatar: profileData.avatar || ''
                      };
                      const res = await api.updateMemberProfile(payload);
                      if (res?.user && setUser) {
                        setUser(prev => ({ ...prev, ...res.user }));
                      }
                      if (refreshUser) refreshUser();
                      setSuccessMsg('Profile updated successfully.');
                      setTimeout(() => setSuccessMsg(''), 4000);
                    } catch (err) {
                      alert(err.message || 'Update failed.');
                    }
                  }}
                  style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
                >
                  {/* Member Profile Photo Upload & Preview */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', padding: '1rem', background: 'var(--bg-secondary, #f8fafc)', borderRadius: '10px', border: '1px solid var(--border-color, #e2e8f0)', flexWrap: 'wrap' }}>
                    <div style={{ position: 'relative', width: '64px', height: '64px', borderRadius: '50%', overflow: 'hidden', border: '2px solid #2563eb', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#eff6ff' }}>
                      {profileData.avatar ? (
                        <img src={profileData.avatar} alt="Profile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                      ) : (
                        <span style={{ fontSize: '1.3rem', fontWeight: 800, color: '#2563eb' }}>
                          {profileData.full_name ? profileData.full_name.charAt(0).toUpperCase() : 'M'}
                        </span>
                      )}
                    </div>
                    <div style={{ flex: 1, minWidth: '180px' }}>
                      <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary, #0f172a)' }}>Member Profile Photo</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted, #64748b)', marginBottom: '0.5rem' }}>Upload your official photo.</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <label className="btn-member-primary" style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
                          <Camera size={13} />
                          <span>Upload Photo</span>
                          <input
                            type="file"
                            accept="image/png, image/jpeg, image/webp"
                            style={{ display: 'none' }}
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) {
                                processAvatarImage(
                                  file,
                                  (dataUrl) => setProfileData(prev => ({ ...prev, avatar: dataUrl })),
                                  (errMsg) => alert(errMsg)
                                );
                              }
                            }}
                          />
                        </label>
                        {profileData.avatar && (
                          <button
                            type="button"
                            className="btn-member-outline"
                            style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                            onClick={() => setProfileData(prev => ({ ...prev, avatar: '' }))}
                          >
                            Remove Photo
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>Full Name *</label>
                    <input
                      type="text"
                      required
                      className="member-search-input"
                      style={{ border: '1px solid #cbd5e1', padding: '0.6rem', borderRadius: '8px', background: 'var(--bg-card, #fff)' }}
                      value={profileData.full_name || ''}
                      onChange={(e) => setProfileData({ ...profileData, full_name: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>Email Address (Read-Only) *</label>
                    <input
                      type="email"
                      disabled
                      readOnly
                      className="member-search-input"
                      style={{ border: '1px solid #e2e8f0', padding: '0.6rem', borderRadius: '8px', background: 'var(--bg-secondary, #f8fafc)', color: 'var(--text-muted, #64748b)', cursor: 'not-allowed' }}
                      value={profileData.email || ''}
                    />
                    <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.25rem' }}>
                      Primary identifier permanently tied to your member account identity. Email cannot be changed.
                    </div>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>Phone Number</label>
                    <input
                      type="text"
                      className="member-search-input"
                      style={{ border: '1px solid #cbd5e1', padding: '0.6rem', borderRadius: '8px', background: '#fff' }}
                      value={profileData.phone_number || ''}
                      onChange={(e) => setProfileData({ ...profileData, phone_number: e.target.value })}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>Preferred Language</label>
                    <select
                      className="member-search-input"
                      style={{ border: '1px solid #cbd5e1', padding: '0.6rem', borderRadius: '8px', background: 'var(--member-card-bg, #fff)', color: 'var(--member-text-main, #0f172a)' }}
                      value={profileData.preferred_language || 'en'}
                      onChange={(e) => {
                        setProfileData({ ...profileData, preferred_language: e.target.value });
                        setLanguage(e.target.value);
                      }}
                    >
                      <option value="en">English (US)</option>
                      <option value="am">አማርኛ (Amharic)</option>
                      <option value="om">Afaan Oromoo (Oromo)</option>
                      <option value="ti">ትግርኛ (Tigrinya)</option>
                    </select>
                  </div>
                  <button type="submit" className="btn-member-primary" style={{ marginTop: '0.5rem' }}>
                    Save Profile Changes
                  </button>
                </form>
              </div>

              {/* Password Change */}
              <div className="member-section-card">
                <div className="member-section-header">
                  <div className="member-section-title">
                    <span>🔒</span>
                    <span>Security & Password</span>
                  </div>
                </div>
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const oldPass = e.target.old_pass.value;
                    const newPass = e.target.new_pass.value;
                    const confirmPass = e.target.confirm_pass.value;
                    if (newPass.length < 8) {
                      alert('New password must be at least 8 characters long.');
                      return;
                    }
                    if (newPass !== confirmPass) {
                      alert('New password confirmation does not match.');
                      return;
                    }
                    try {
                      await api.changeMemberPassword(oldPass, newPass);
                      setSuccessMsg('Password changed successfully.');
                      setTimeout(() => setSuccessMsg(''), 4000);
                      e.target.reset();
                    } catch (err) {
                      alert(err.message || 'Password change failed.');
                    }
                  }}
                  style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
                >
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>Current Password *</label>
                    <input
                      name="old_pass"
                      type="password"
                      required
                      className="member-search-input"
                      style={{ border: '1px solid #cbd5e1', padding: '0.6rem', borderRadius: '8px', background: 'var(--bg-card, #fff)' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>New Password (min 8 chars) *</label>
                    <input
                      name="new_pass"
                      type="password"
                      required
                      className="member-search-input"
                      style={{ border: '1px solid #cbd5e1', padding: '0.6rem', borderRadius: '8px', background: 'var(--bg-card, #fff)' }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>Confirm New Password *</label>
                    <input
                      name="confirm_pass"
                      type="password"
                      required
                      className="member-search-input"
                      style={{ border: '1px solid #cbd5e1', padding: '0.6rem', borderRadius: '8px', background: 'var(--bg-card, #fff)' }}
                    />
                  </div>
                  <button type="submit" className="btn-member-primary" style={{ marginTop: '0.5rem' }}>
                    Update Password
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* =================================================================
              TAB 11: HELP & SUPPORT
              ================================================================= */}
          {activeTab === 'help' && (
            <div className="member-section-card">
              <div className="member-section-header">
                <div className="member-section-title">
                  <Headphones size={22} color="#2563eb" />
                  <span>Frequently Asked Questions & Support</span>
                </div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ border: '1px solid #e2e8f0', borderRadius: '10px', padding: '1rem' }}>
                  <h4 style={{ margin: 0, fontWeight: 700, color: '#1e3a8a' }}>How does Digital Equb guarantee payment safety?</h4>
                  <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem', color: '#475569' }}>
                    Every contribution is tracked via immutable double-entry ledger entries. Cash payments require dual confirmation (Treasurer + independent verification), while bank transfers undergo reference reconciliation.
                  </p>
                </div>
                <div style={{ border: '1px solid #e2e8f0', borderRadius: '10px', padding: '1rem' }}>
                  <h4 style={{ margin: 0, fontWeight: 700, color: '#1e3a8a' }}>How do I download my contribution receipt?</h4>
                  <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem', color: '#475569' }}>
                    Visit the "Payment History" tab, click "View Slip" on any confirmed payment, and print or download your electronic receipt slip with verification details.
                  </p>
                </div>
                <div style={{ border: '1px solid #e2e8f0', borderRadius: '10px', padding: '1rem' }}>
                  <h4 style={{ margin: 0, fontWeight: 700, color: '#1e3a8a' }}>What if my bank transfer is delayed?</h4>
                  <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem', color: '#475569' }}>
                    Submit a dispute under the "Disputes" tab with your CBE/Telebirr reference number. Your group organizer and treasurer will verify your payment against the group statement.
                  </p>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ====================================================================
          MODAL 1: MAKE PAYMENT MODAL
          ==================================================================== */}
      {paymentModalOpen && selectedObligationToPay && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
          <div style={{ background: '#fff', borderRadius: '16px', maxWidth: '500px', width: '100%', padding: '1.75rem', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800 }}>Make Contribution Payment</h3>
              <button type="button" onClick={() => setPaymentModalOpen(false)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}><X size={20} /></button>
            </div>

            <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '10px', marginBottom: '1.25rem', border: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Group: {selectedObligationToPay.group_name}</div>
              <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#0f172a', margin: '0.25rem 0' }}>
                {formatETB(selectedObligationToPay.remaining_amount || selectedObligationToPay.expected_amount)}
              </div>
              <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Round #{selectedObligationToPay.period_number} • Due: {selectedObligationToPay.due_date}</div>
            </div>

            {/* Payment Method Selector */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>Choose Contribution Method</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setPaymentMethodChoice('DIGITAL')}
                  style={{
                    padding: '0.65rem 0.5rem',
                    borderRadius: '8px',
                    border: paymentMethodChoice === 'DIGITAL' ? '2px solid #2563eb' : '1px solid #e2e8f0',
                    background: paymentMethodChoice === 'DIGITAL' ? '#eff6ff' : '#fff',
                    fontWeight: 600,
                    fontSize: '0.8rem',
                    cursor: 'pointer'
                  }}
                >
                  Chapa Gateway
                </button>
                <button
                  type="button"
                  onClick={() => setPaymentMethodChoice('BANK_TRANSFER')}
                  style={{
                    padding: '0.65rem 0.5rem',
                    borderRadius: '8px',
                    border: paymentMethodChoice === 'BANK_TRANSFER' ? '2px solid #2563eb' : '1px solid #e2e8f0',
                    background: paymentMethodChoice === 'BANK_TRANSFER' ? '#eff6ff' : '#fff',
                    fontWeight: 600,
                    fontSize: '0.8rem',
                    cursor: 'pointer'
                  }}
                >
                  Bank Transfer
                </button>
                <button
                  type="button"
                  onClick={() => setPaymentMethodChoice('CASH')}
                  style={{
                    padding: '0.65rem 0.5rem',
                    borderRadius: '8px',
                    border: paymentMethodChoice === 'CASH' ? '2px solid #2563eb' : '1px solid #e2e8f0',
                    background: paymentMethodChoice === 'CASH' ? '#eff6ff' : '#fff',
                    fontWeight: 600,
                    fontSize: '0.8rem',
                    cursor: 'pointer'
                  }}
                >
                  Cash In-Hand
                </button>
              </div>
            </div>

            {/* Method A Form */}
            {paymentMethodChoice === 'DIGITAL' && (
              <div style={{ fontSize: '0.85rem', color: '#166534', marginBottom: '1.25rem', background: '#f0fdf4', padding: '0.85rem', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
                <div style={{ fontWeight: 700, marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <CheckCircle2 size={16} color="#16a34a" /> Official Chapa Payment Gateway
                </div>
                <div>Direct digital checkout via Chapa (Ethiopian debit cards, Telebirr, CBE Birr, Awash, and mobile money). You will be redirected to the secure Chapa payment portal.</div>

                {selectedObligationToPay.has_subaccount ? (
                  <div style={{ marginTop: '0.75rem', padding: '0.6rem 0.75rem', background: '#dcfce7', borderRadius: '6px', border: '1px solid #86efac', color: '#15803d' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      🏦 Group Common Account Settlement Verified
                    </div>
                    <div style={{ fontSize: '0.78rem', marginTop: '0.25rem' }}>
                      Group Bank: <strong>{selectedObligationToPay.bank_name || 'Commercial Bank of Ethiopia (CBE)'}</strong><br />
                      Account: <strong>{selectedObligationToPay.bank_account_number}</strong> ({selectedObligationToPay.bank_account_name || selectedObligationToPay.group_name})
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#166534', marginTop: '0.35rem' }}>
                      ✓ 100% of contribution settles straight into this group's common account via Chapa Subaccount.
                    </div>
                  </div>
                ) : (
                  <div style={{ marginTop: '0.75rem', padding: '0.5rem 0.75rem', background: '#ffffff', borderRadius: '6px', border: '1px solid #e2e8f0', color: '#64748b', fontSize: '0.78rem' }}>
                    🛡️ Group funds belong exclusively to your Equb group and remain strictly isolated from platform rent.
                  </div>
                )}
              </div>
            )}

            {/* Method B Form */}
            {paymentMethodChoice === 'BANK_TRANSFER' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <div style={{ fontSize: '0.8rem', background: '#eff6ff', padding: '0.75rem', borderRadius: '8px', color: '#1e40af', border: '1px solid #bfdbfe' }}>
                  Transfer directly to Group Common Account:<br />
                  <strong>Bank:</strong> {selectedObligationToPay.bank_name || 'Commercial Bank of Ethiopia (CBE)'}<br />
                  <strong>Account:</strong> {selectedObligationToPay.bank_account_number || '100023456789'}<br />
                  <strong>Name:</strong> {selectedObligationToPay.bank_account_name || selectedObligationToPay.group_name}
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.25rem' }}>Bank Transfer Reference Number *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CBE-ET-987654"
                    value={transferRef}
                    onChange={(e) => setTransferRef(e.target.value)}
                    className="member-search-input"
                    style={{ border: '1px solid #cbd5e1', padding: '0.55rem', borderRadius: '6px', background: '#fff' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.25rem' }}>Notes / Depositor Name</label>
                  <input
                    type="text"
                    placeholder="Optional notes"
                    value={transferNotes}
                    onChange={(e) => setTransferNotes(e.target.value)}
                    className="member-search-input"
                    style={{ border: '1px solid #cbd5e1', padding: '0.55rem', borderRadius: '6px', background: '#fff' }}
                  />
                </div>
              </div>
            )}

            {/* Method C Form */}
            {paymentMethodChoice === 'CASH' && (
              <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '1.25rem', background: '#fff7ed', padding: '0.85rem', borderRadius: '8px', border: '1px solid #fed7aa' }}>
                Please hand the exact cash amount of <strong>{formatETB(selectedObligationToPay.remaining_amount || selectedObligationToPay.expected_amount)}</strong> directly to Group Treasurer <strong>Abebe Kebede</strong>. The treasurer will record the receipt for dual-confirmation.
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn-member-outline"
                onClick={() => setPaymentModalOpen(false)}
              >
                Cancel
              </button>
              {paymentMethodChoice !== 'CASH' && (
                <button
                  type="button"
                  className="btn-member-primary"
                  onClick={handleExecutePayment}
                >
                  Confirm & Submit Payment
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODAL 2: PRINTABLE OFFICIAL ELECTRONIC RECEIPT SLIP
          ==================================================================== */}
      {receiptModalOpen && activeReceiptSlip && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
          <div style={{ background: '#fff', borderRadius: '16px', maxWidth: '550px', width: '100%', padding: '2rem', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)' }}>
            <div className="member-printable-receipt-slip" style={{ border: '2px dashed #cbd5e1', padding: '1.5rem', borderRadius: '12px' }}>
              <div style={{ textAlign: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '1rem' }}>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#1e3a8a' }}>DIGITAL EQUB ETHIOPIA</div>
                <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Official Electronic Contribution Receipt</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, marginTop: '0.5rem', fontFamily: 'monospace' }}>
                  {activeReceiptSlip.receipt_number}
                </div>
              </div>

              <div style={{ margin: '1.25rem 0', display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Payer:</span>
                  <span style={{ fontWeight: 700 }}>{activeReceiptSlip.payer_name}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Equb Group:</span>
                  <span style={{ fontWeight: 700 }}>{activeReceiptSlip.group_name}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Contribution Round:</span>
                  <span style={{ fontWeight: 600 }}>Round #{activeReceiptSlip.round_number}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Method:</span>
                  <span>{activeReceiptSlip.payment_method}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Reference:</span>
                  <span style={{ fontFamily: 'monospace' }}>{activeReceiptSlip.transfer_reference}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: '#64748b' }}>Payment Date:</span>
                  <span>{activeReceiptSlip.payment_date}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #e2e8f0', paddingTop: '0.5rem', fontSize: '1.15rem' }}>
                  <span style={{ fontWeight: 800 }}>Amount Confirmed:</span>
                  <span style={{ fontWeight: 800, color: '#15803d' }}>{formatETB(activeReceiptSlip.amount)}</span>
                </div>
              </div>

              <div style={{ textAlign: 'center', fontSize: '0.75rem', color: '#94a3b8', borderTop: '1px solid #e2e8f0', paddingTop: '0.75rem' }}>
                Verified by: {activeReceiptSlip.verified_by} • Secured by Digital Equb Immutable Ledger
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.25rem' }}>
              <button type="button" className="btn-member-outline" onClick={() => setReceiptModalOpen(false)}>
                Close
              </button>
              <button
                type="button"
                className="btn-member-primary"
                onClick={() => window.print()}
              >
                <Printer size={16} /> Print / Save PDF
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODAL 3: VIEW RULES & VOTE MODAL
          ==================================================================== */}
      {rulesModalOpen && activeRulesGroup && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
          <div style={{ background: '#fff', borderRadius: '16px', maxWidth: '600px', width: '100%', maxHeight: '85vh', overflowY: 'auto', padding: '1.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800 }}>Rules for {activeRulesGroup.name}</h3>
              <button type="button" onClick={() => setRulesModalOpen(false)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}><X size={20} /></button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {activeRulesVersions.map(rv => (
                <div key={rv.id} style={{ border: '1px solid #e2e8f0', borderRadius: '12px', padding: '1rem', background: rv.is_active ? '#eff6ff' : '#fff' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontWeight: 700 }}>Version {rv.version_number}: {rv.title}</div>
                    <span className="member-status-pill">{rv.status}</span>
                  </div>
                  <p style={{ fontSize: '0.88rem', color: '#334155', marginTop: '0.5rem', lineHeight: 1.5 }}>{rv.terms_text}</p>
                  
                  {/* Voting UI if Proposed */}
                  {rv.status === 'PROPOSED' && (
                    <div style={{ marginTop: '0.75rem', borderTop: '1px solid #e2e8f0', paddingTop: '0.75rem' }}>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.4rem' }}>Member Approval Vote</div>
                      {rv.my_vote ? (
                        <div style={{ fontSize: '0.85rem', color: '#15803d', fontWeight: 600 }}>
                          ✓ You voted {rv.my_vote.decision} on {rv.my_vote.decided_at}
                        </div>
                      ) : (
                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                          <button
                            type="button"
                            className="btn-member-primary"
                            style={{ background: '#10b981', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                            onClick={() => handleVoteRule(rv.id, 'APPROVED')}
                          >
                            <ThumbsUp size={14} /> Approve Rules
                          </button>
                          <button
                            type="button"
                            className="btn-member-outline"
                            style={{ color: '#ef4444', borderColor: '#ef4444', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
                            onClick={() => handleVoteRule(rv.id, 'REJECTED')}
                          >
                            <ThumbsDown size={14} /> Reject
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div style={{ textAlign: 'right', marginTop: '1rem' }}>
              <button type="button" className="btn-member-outline" onClick={() => setRulesModalOpen(false)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* ====================================================================
          MODAL 4: SUBMIT DISPUTE MODAL
          ==================================================================== */}
      {disputeModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
          <div style={{ background: '#fff', borderRadius: '16px', maxWidth: '500px', width: '100%', padding: '1.75rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800 }}>Submit a Dispute / Grievance</h3>
              <button type="button" onClick={() => setDisputeModalOpen(false)} style={{ border: 'none', background: 'none', cursor: 'pointer' }}><X size={20} /></button>
            </div>

            <form onSubmit={handleSubmitDispute} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>Select Equb Group *</label>
                <select
                  required
                  className="member-search-input"
                  style={{ border: '1px solid #cbd5e1', padding: '0.6rem', borderRadius: '8px', background: '#fff' }}
                  value={disputeForm.group_id}
                  onChange={(e) => setDisputeForm({ ...disputeForm, group_id: e.target.value })}
                >
                  <option value="">-- Choose Group --</option>
                  {(dashboardData?.my_groups || []).map(g => (
                    <option key={g.id} value={g.id}>{g.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>Category *</label>
                <select
                  className="member-search-input"
                  style={{ border: '1px solid #cbd5e1', padding: '0.6rem', borderRadius: '8px', background: '#fff' }}
                  value={disputeForm.category}
                  onChange={(e) => setDisputeForm({ ...disputeForm, category: e.target.value })}
                >
                  <option value="PAYMENT_NOT_RECORDED">Payment Not Recorded or Credited</option>
                  <option value="INCORRECT_AMOUNT">Incorrect Obligation Amount</option>
                  <option value="PAYOUT_ORDER_DISPUTE">Payout Order / Rotation Dispute</option>
                  <option value="RULE_VIOLATION">Rule Violation</option>
                  <option value="OTHER">Other Issue</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>Subject / Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Uncredited bank transfer CBE-987"
                  className="member-search-input"
                  style={{ border: '1px solid #cbd5e1', padding: '0.6rem', borderRadius: '8px', background: '#fff' }}
                  value={disputeForm.title}
                  onChange={(e) => setDisputeForm({ ...disputeForm, title: e.target.value })}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.3rem' }}>Description *</label>
                <textarea
                  required
                  rows={4}
                  placeholder="Describe your dispute with dates, references, or details..."
                  className="member-search-input"
                  style={{ border: '1px solid #cbd5e1', padding: '0.6rem', borderRadius: '8px', background: '#fff', resize: 'vertical' }}
                  value={disputeForm.description}
                  onChange={(e) => setDisputeForm({ ...disputeForm, description: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button type="button" className="btn-member-outline" onClick={() => setDisputeModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn-member-primary">Submit Dispute</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ====================================================================
          MOBILE BOTTOM NAVIGATION (Home, My Groups, Payments, Notifs, Profile)
          ==================================================================== */}
      <nav className="member-mobile-bottom-bar">
        <button
          type="button"
          className={`member-mobile-nav-btn ${activeTab === 'home' ? 'active' : ''}`}
          onClick={() => setActiveTab('home')}
        >
          <Home size={20} />
          <span>Home</span>
        </button>
        <button
          type="button"
          className={`member-mobile-nav-btn ${activeTab === 'groups' ? 'active' : ''}`}
          onClick={() => setActiveTab('groups')}
        >
          <Users size={20} />
          <span>Groups</span>
        </button>
        <button
          type="button"
          className={`member-mobile-nav-btn ${activeTab === 'contributions' || activeTab === 'payments' ? 'active' : ''}`}
          onClick={() => setActiveTab('contributions')}
        >
          <Wallet size={20} />
          <span>Payments</span>
        </button>
        <button
          type="button"
          className={`member-mobile-nav-btn ${activeTab === 'notifications' ? 'active' : ''}`}
          onClick={() => setActiveTab('notifications')}
        >
          <Bell size={20} />
          <span>Alerts</span>
          {dashboardData?.badges?.unread_notifications > 0 && (
            <span className="member-notif-dot" style={{ top: '-4px', right: '4px' }}>
              {dashboardData.badges.unread_notifications}
            </span>
          )}
        </button>
        <button
          type="button"
          className={`member-mobile-nav-btn ${activeTab === 'profile' ? 'active' : ''}`}
          onClick={() => setActiveTab('profile')}
        >
          <Settings size={20} />
          <span>Profile</span>
        </button>
      </nav>
    </div>
  );
}

