import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { HeaderControls } from '../components/HeaderControls';
import { NotificationCenter } from '../components/NotificationCenter';
import { processAvatarImage } from '../utils/imageHelper';
import './OrganizerDashboard.css';
import {
  LayoutDashboard,
  Users,
  UserCheck,
  CircleDollarSign,
  CreditCard,
  Crown,
  BarChart3,
  ShieldCheck,
  Settings,
  Headphones,
  Menu,
  Bell,
  ChevronDown,
  Plus,
  ArrowUpRight,
  TrendingUp,
  Clock,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Copy,
  Download,
  Calendar,
  Search,
  Filter,
  LogOut,
  User,
  Shield,
  ShieldAlert,
  HelpCircle,
  MoreVertical,
  Briefcase,
  Home,
  Check,
  X,
  Edit2,
  Printer,
  RefreshCw,
  FileText,
  Camera,
  Trash2,
  Lock,
  Landmark,
  Wallet,
  Award,
  AlertTriangle,
  Sparkles,
  Hash,
  XCircle
} from 'lucide-react';

const MASTER_ETHIOPIAN_BANKS = [
  { id: 946, name: "Commercial Bank of Ethiopia (CBE)", code: "CBETETAA" },
  { id: 855, name: "telebirr", code: "ETHIOTEL" },
  { id: 128, name: "CBEBirr", code: "CBEBIRR" },
  { id: 656, name: "Awash Bank", code: "AWINETAA" },
  { id: 347, name: "Bank of Abyssinia", code: "ABYSETAA" },
  { id: 206, name: "Dashen Bank", code: "DASHETAA" },
  { id: 836, name: "Cooperative Bank of Oromia", code: "CBORETAA" },
  { id: 249, name: "Bunna Bank", code: "BUNAETAA" },
  { id: 130, name: "Abay Bank", code: "ABAYETAA" },
  { id: 301, name: "Nib International Bank", code: "NIBIETAA" },
  { id: 534, name: "Hibret Bank (United Bank)", code: "UNITEDETAA" },
  { id: 902, name: "Zemen Bank", code: "ZEMNETAA" },
  { id: 752, name: "Oromia Bank", code: "OROBETAA" },
  { id: 231, name: "Berhan Bank", code: "BERHETAA" },
  { id: 772, name: "Addis International Bank", code: "ABSCETAA" },
  { id: 395, name: "Enat Bank", code: "ENATETAA" },
  { id: 405, name: "Lion International Bank", code: "LIONETAA" },
  { id: 422, name: "Wegagen Bank", code: "WEGAETAA" },
  { id: 382, name: "Global Bank Ethiopia", code: "GLBAETAA" },
  { id: 801, name: "Siinqee Bank", code: "SINQEETAA" },
  { id: 554, name: "Hijra Bank (Interest-Free)", code: "HIJRAETAA" },
  { id: 991, name: "ZamZam Bank (Interest-Free)", code: "ZAMZAMETAA" },
  { id: 887, name: "Tsedey Bank", code: "TSDYETAA" },
  { id: 923, name: "Amhara Bank", code: "AMHAETAA" },
  { id: 471, name: "Goh Betoch Bank", code: "GOHBETAA" },
  { id: 610, name: "Rammis Bank", code: "RAMMETAA" },
  { id: 789, name: "Sidama Bank", code: "SIDMETAA" },
  { id: 286, name: "M-Pesa (Safaricom)", code: "MPESA" },
  { id: 867, name: "YaYaWallet", code: "YAYAWALLET" },
  { id: 312, name: "E-Birr", code: "EBIRR" }
];

export function OrganizerDashboard() {
  const { user, setUser, logout, setCurrentInterface, setRole, refreshUser } = useAuth();
  const { language, setLanguage, t } = useLanguage();
  const { effectiveTheme } = useTheme();

  // Navigation state (persisted across browser reloads)
  const [activeTab, setActiveTabState] = useState(() => {
    if (typeof window !== 'undefined') {
      const urlParams = new URLSearchParams(window.location.search);
      const tabParam = urlParams.get('tab') || urlParams.get('amp;tab');
      if (tabParam) return tabParam;
      return sessionStorage.getItem('org_active_tab') || 'dashboard';
    }
    return 'dashboard';
  });

  const setActiveTab = (tab) => {
    setActiveTabState(tab);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem('org_active_tab', tab);
    }
  };

  const [sidebarOpen, setSidebarOpen] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth > 1024;
    }
    return true;
  });
  const [refreshing, setRefreshing] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  // Data states
  const [dashData, setDashData] = useState(null);
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [groupMembers, setGroupMembers] = useState([]);
  const [membershipRequests, setMembershipRequests] = useState([]);
  const [treasurerInfo, setTreasurerInfo] = useState(null);
  const [groupRules, setGroupRules] = useState([]);
  const [groupContributions, setGroupContributions] = useState(null);
  const [groupPayouts, setGroupPayouts] = useState([]);
  const [groupDisputes, setGroupDisputes] = useState([]);
  const [subscriptionData, setSubscriptionData] = useState(null);
  const [verificationData, setVerificationData] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [supportTickets, setSupportTickets] = useState([]);

  // UI / Form states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Modals
  const [showCreateGroupModal, setShowCreateGroupModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showAddMemberModal, setShowAddMemberModal] = useState(false);
  const [showMemberDetailModal, setShowMemberDetailModal] = useState(false);
  const [showEditGroupModal, setShowEditGroupModal] = useState(false);
  const [showSchedulePayoutModal, setShowSchedulePayoutModal] = useState(false);
  const [showAssignTreasurerModal, setShowAssignTreasurerModal] = useState(false);
  const [showProposeRuleModal, setShowProposeRuleModal] = useState(false);
  const [showSupportTicketModal, setShowSupportTicketModal] = useState(false);
  const [showVerificationModal, setShowVerificationModal] = useState(false);
  const [showGroupDetailsModal, setShowGroupDetailsModal] = useState(false);
  const [showSubaccountModal, setShowSubaccountModal] = useState(false);
  const [subaccountLoading, setSubaccountLoading] = useState(false);
  const [supportedBanks, setSupportedBanks] = useState(MASTER_ETHIOPIAN_BANKS);
  const [subaccountForm, setSubaccountForm] = useState({
    bank_code: '',
    bank_name: '',
    account_name: '',
    account_number: '',
    business_name: ''
  });
  const [subaccountInfo, setSubaccountInfo] = useState(null);

  // Personal Contribution Obligations & Payment state
  const [personalObligations, setPersonalObligations] = useState([]);
  const [personalContributionFilter, setPersonalContributionFilter] = useState('ALL');
  const [personalSelectedGroupId, setPersonalSelectedGroupId] = useState('ALL');
  const [showPersonalPaymentModal, setShowPersonalPaymentModal] = useState(false);
  const [selectedPersonalObligation, setSelectedPersonalObligation] = useState(null);
  const [personalPaymentMethod, setPersonalPaymentMethod] = useState('DIGITAL'); // 'DIGITAL' | 'BANK_TRANSFER' | 'CASH'
  const [personalTransferRef, setPersonalTransferRef] = useState('');
  const [personalTransferNotes, setPersonalTransferNotes] = useState('');
  const [payingPersonalObligation, setPayingPersonalObligation] = useState(false);

  // Group payouts and reports states
  const [groupPayoutsData, setGroupPayoutsData] = useState(null);
  const [payoutStatusFilter, setPayoutStatusFilter] = useState('ALL');
  const [selectedReportType, setSelectedReportType] = useState('COMPLIANCE');

  // Add Member State
  const [addMemberForm, setAddMemberForm] = useState({
    full_name: '',
    email: '',
    phone_number: '',
    password_setup_method: 'TEMPORARY_PASSWORD',
    initial_password: ''
  });
  const [addMemberResult, setAddMemberResult] = useState(null);

  // Member Detail & Actions State
  const [selectedMemberDetail, setSelectedMemberDetail] = useState(null);
  const [loadingMemberDetail, setLoadingMemberDetail] = useState(false);
  const [memberDetailForm, setMemberDetailForm] = useState({
    full_name: '',
    phone_number: '',
    payout_order_index: 1,
    status: 'ACTIVE'
  });

  // Edit Group State
  const [editGroupForm, setEditGroupForm] = useState({
    id: '',
    name: '',
    description: '',
    group_purpose: '',
    capacity: 20
  });

  // Settings State
  const [settingsForm, setSettingsForm] = useState({
    full_name: '',
    email: '',
    phone_number: '',
    preferred_language: 'en',
    avatar: '',
    current_password: '',
    new_password: '',
    confirm_new_password: '',
    change_password: false,
    notify_in_app: true,
    notify_email: true,
    notify_sms: true
  });
  const [settingsSaving, setSettingsSaving] = useState(false);

  // Sync settingsForm with logged in user
  useEffect(() => {
    if (user) {
      setSettingsForm(prev => ({
        ...prev,
        full_name: user.full_name || '',
        email: user.email || '',
        phone_number: user.phone_number || '',
        preferred_language: user.preferred_language || 'en',
        avatar: user.avatar || ''
      }));
    }
  }, [user]);

  // Forms
  const [createGroupForm, setCreateGroupForm] = useState({
    name: '',
    description: '',
    group_purpose: '',
    currency: 'ETB',
    contribution_amount: '5000.00',
    contribution_frequency: 'MONTHLY',
    capacity: 20,
    start_date: new Date().toISOString().split('T')[0],
    payout_method: 'LOTTERY_DRAW',
    lottery_method: 'METHOD_A',
    grace_period_days: 3,
    rules_approval_threshold_percent: 100,
    require_cash_second_confirmation: true,
    participate_as_member: true,
    rules_terms: ''
  });

  // Lottery & Cycle Management State
  const [lotteryData, setLotteryData] = useState(null);
  const [lotteryLoading, setLotteryLoading] = useState(false);
  const [drawingLottery, setDrawingLottery] = useState(false);
  const [startingCycle, setStartingCycle] = useState(false);

  // Overdue Contributions Resolution System State (Dropdown 2: A, B, C)
  const [overdueCases, setOverdueCases] = useState([]);
  const [overdueCategoryFilter, setOverdueCategoryFilter] = useState('ALL');
  const [overdueLoading, setOverdueLoading] = useState(false);
  const [evaluatingOverdue, setEvaluatingOverdue] = useState(false);
  const [showResolveModal, setShowResolveModal] = useState(false);
  const [selectedOverdueCase, setSelectedOverdueCase] = useState(null);
  const [resolutionChoice, setResolutionChoice] = useState('CONTINUE_WAITING'); // CONTINUE_WAITING, PAYMENT_AGREEMENT, MEMBERSHIP_REVIEW
  const [waitingDays, setWaitingDays] = useState(3);
  const [waitingReason, setWaitingReason] = useState('Granted grace period extension upon member consultation.');
  const [agreementReason, setAgreementReason] = useState('Structured installment recovery agreement.');
  const [agreementInstallments, setAgreementInstallments] = useState([
    { amount: '2500', due_date: new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0] },
    { amount: '2500', due_date: new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0] }
  ]);
  const [reviewReason, setReviewReason] = useState('Persistent non-contribution exceeding grace period.');
  const [reviewDecision, setReviewDecision] = useState('REPLACE_MEMBER'); // REMOVE_MEMBER, REPLACE_MEMBER, REINSTATE_MEMBER
  const [replacementUserId, setReplacementUserId] = useState('');
  const [resolvingCase, setResolvingCase] = useState(false);

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteResult, setInviteResult] = useState(null);

  const [payoutForm, setPayoutForm] = useState({
    recipient_membership_id: '',
    amount: '',
    notes: ''
  });

  const [selectedTreasurerMemberId, setSelectedTreasurerMemberId] = useState('');

  const [ruleProposalForm, setRuleProposalForm] = useState({
    title: '',
    terms_text: '',
    contribution_amount: '5000.00',
    contribution_frequency: 'MONTHLY',
    payout_method: 'ROTATION_ORDER',
    approval_threshold_percent: 100
  });

  const [supportTicketForm, setSupportTicketForm] = useState({
    subject: '',
    category: 'TECHNICAL',
    message: '',
    group_id: '',
    evidence_notes: ''
  });

  const [verificationNotes, setVerificationNotes] = useState('');

  // Subscription Rent Payment Gate States
  const [payingSubscription, setPayingSubscription] = useState(false);
  const [selectedPaymentProvider, setSelectedPaymentProvider] = useState('CHAPA');
  const [paymentPhone, setPaymentPhone] = useState('');
  const [paymentReference, setPaymentReference] = useState('');

  const handlePaySubscription = async (e, targetPlanId = null) => {
    if (e && e.preventDefault) e.preventDefault();
    try {
      setPayingSubscription(true);
      setError('');
      const planId = targetPlanId || dashData?.assigned_plan_id || subscriptionData?.subscription?.plan?.id;
      const res = await api.payOrganizerSubscription({ plan_id: planId });
      if (res.is_free_starter) {
        setSuccessMsg(res.message || 'Starter plan active with 0.00 ETB rent fee. Workspace unlocked!');
        await loadOverviewData();
        return;
      }
      if (res.checkout_url) {
        setSuccessMsg(`Chapa checkout session initiated! (Ref: ${res.tx_ref}). Redirecting to Chapa payment portal...`);
        window.location.href = res.checkout_url;
        return;
      }
      setSuccessMsg(res.message || 'Subscription payment initiated via Chapa.');
      await loadOverviewData();
    } catch (err) {
      setError(err.message || 'Chapa payment processing failed. Please retry.');
    } finally {
      setPayingSubscription(false);
    }
  };

  // Personal Contribution Payment Handlers
  const loadPersonalContributions = async () => {
    try {
      const res = await api.getMyObligations();
      setPersonalObligations(Array.isArray(res) ? res : (res?.results || []));
    } catch (err) {
      console.error('Failed to load personal contributions:', err);
    }
  };

  const handleInitiatePersonalPayment = (obligation) => {
    setSelectedPersonalObligation(obligation);
    setPersonalPaymentMethod('DIGITAL');
    setPersonalTransferRef('');
    setPersonalTransferNotes('');
    setShowPersonalPaymentModal(true);
  };

  const handleExecutePersonalPayment = async () => {
    if (!selectedPersonalObligation) return;
    try {
      setPayingPersonalObligation(true);
      setError('');
      if (personalPaymentMethod === 'DIGITAL') {
        const res = await api.payDigital(selectedPersonalObligation.id, 'CHAPA');
        if (res.checkout_url) {
          setSuccessMsg(`Chapa checkout session initiated! (Ref: ${res.tx_ref || res.internal_reference}). Redirecting to payment portal...`);
          setShowPersonalPaymentModal(false);
          window.location.href = res.checkout_url;
          return;
        } else {
          setSuccessMsg(`Chapa payment initiated successfully! Internal Ref: ${res.internal_reference || res.tx_ref}.`);
        }
      } else if (personalPaymentMethod === 'BANK_TRANSFER') {
        if (!personalTransferRef.trim()) {
          alert('Please enter your bank transfer reference number.');
          setPayingPersonalObligation(false);
          return;
        }
        await api.submitBankTransfer(selectedPersonalObligation.id, {
          transfer_reference: personalTransferRef,
          notes: personalTransferNotes
        });
        setSuccessMsg(`Bank transfer ${personalTransferRef} submitted for treasurer reconciliation.`);
      }
      setShowPersonalPaymentModal(false);
      await loadPersonalContributions();
      if (selectedGroup) {
        await loadGroupSubData(selectedGroup.id);
      }
    } catch (err) {
      setError(err.message || 'Payment submission failed.');
    } finally {
      setPayingPersonalObligation(false);
    }
  };

  // Initial Load & Chapa Verification Return
  useEffect(() => {
    const rawSearch = window.location.search || '';
    const cleanSearch = rawSearch.replace(/&amp;/g, '&');
    const urlParams = new URLSearchParams(cleanSearch);
    const txRef = urlParams.get('tx_ref') || urlParams.get('amp;tx_ref');
    const tabParam = urlParams.get('tab') || urlParams.get('amp;tab');
    if (tabParam) {
      setActiveTab(tabParam);
    }

    if (txRef && (txRef.startsWith('SUB-ORG-') || txRef.includes('SUB-'))) {
      const verifyReturn = async () => {
        try {
          setLoading(true);
          const verRes = await api.verifyOrganizerSubscription(txRef);
          if (verRes.status === 'CONFIRMED' || verRes.subscription_status === 'ACTIVE' || verRes.already_confirmed) {
            setSuccessMsg(`Subscription rent payment confirmed via Chapa! Receipt #${verRes.receipt_number || txRef}. Workspace unlocked.`);
            if (refreshUser) {
              await refreshUser();
            }
          } else {
            setError(`Chapa subscription status: ${verRes.status || 'Verification pending'}.`);
          }
        } catch (err) {
          setError(err.message || 'Chapa subscription verification failed.');
        } finally {
          window.history.replaceState({}, document.title, window.location.pathname);
          await loadOverviewData();
          await loadPersonalContributions();
        }
      };
      verifyReturn();
    } else if (txRef && (txRef.startsWith('EQUB-') || txRef.includes('EQUB-'))) {
      const verifyReturn = async () => {
        try {
          setLoading(true);
          const verRes = await api.verifyChapaPayment(txRef);
          if (verRes.status === 'CONFIRMED' || verRes.success) {
            setSuccessMsg(`Personal group contribution payment confirmed via Chapa! Receipt #${verRes.receipt_number || txRef}. Group funds allocated.`);
          } else {
            setError(`Chapa contribution status: ${verRes.status || 'Verification pending'}.`);
          }
        } catch (err) {
          setError(err.message || 'Chapa contribution verification failed.');
        } finally {
          window.history.replaceState({}, document.title, window.location.pathname);
          await loadOverviewData();
          await loadPersonalContributions();
        }
      };
      verifyReturn();
    } else {
      loadOverviewData();
      loadPersonalContributions();
    }
  }, []);

  const loadOverviewData = async () => {
    try {
      setLoading(true);
      setError('');
      loadPersonalContributions();
      const [dashRes, grpsRes, subRes, verifRes] = await Promise.allSettled([
        api.getOrganizerDashboard(),
        api.getOrganizerGroups(),
        api.getOrganizerSubscription(),
        api.getOrganizerVerification()
      ]);

      if (dashRes.status === 'fulfilled' && dashRes.value) {
        setDashData(dashRes.value);
      } else if (dashRes.status === 'rejected') {
        setError(dashRes.reason?.message || 'Failed to load organizer dashboard overview.');
      }

      if (grpsRes.status === 'fulfilled' && grpsRes.value) {
        setGroups(grpsRes.value.groups || []);
        const firstGroup = grpsRes.value.groups?.[0];
        if (firstGroup) {
          setSelectedGroup(firstGroup);
          loadGroupSubData(firstGroup.id);
        }
      }

      if (subRes.status === 'fulfilled' && subRes.value) {
        setSubscriptionData(subRes.value);
      }

      if (verifRes.status === 'fulfilled' && verifRes.value) {
        setVerificationData(verifRes.value);
      }
    } catch (err) {
      setError(err.message || 'Failed to initialize organizer dashboard.');
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshAll = async () => {
    try {
      setRefreshing(true);
      setError('');
      await Promise.all([
        loadOverviewData(),
        loadPersonalContributions(),
        selectedGroup?.id ? loadGroupSubData(selectedGroup.id) : Promise.resolve(),
        refreshUser ? refreshUser() : Promise.resolve()
      ]);
      setSuccessMsg(t('dataRefreshedMsg') || 'Dashboard data refreshed successfully!');
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to refresh data. Please retry.');
    } finally {
      setRefreshing(false);
    }
  };

  const loadGroupSubData = async (groupId) => {
    if (!groupId) return;
    try {
      const [membersRes, reqsRes, treasRes, rulesRes, contribRes, payoutsRes, disputesRes, repRes, lotRes, ovRes] = await Promise.all([
        api.getOrganizerGroupMembers(groupId).catch(() => ({ members: [] })),
        api.getOrganizerMembershipRequests(groupId).catch(() => ({ pending_requests: [] })),
        api.getOrganizerTreasurer(groupId).catch(() => null),
        api.getOrganizerGroupRules(groupId).catch(() => ({ rule_versions: [] })),
        api.getOrganizerGroupContributions(groupId).catch(() => null),
        api.getOrganizerGroupPayouts(groupId).catch(() => ({ payouts: [] })),
        api.getOrganizerGroupDisputes(groupId).catch(() => []),
        api.getOrganizerGroupReports(groupId).catch(() => null),
        api.getOrganizerLottery(groupId).catch(() => null),
        api.getOrganizerOverdueCases(groupId).catch(() => [])
      ]);

      setGroupMembers(membersRes.members || []);
      setMembershipRequests(reqsRes.pending_requests || []);
      setTreasurerInfo(treasRes);
      setGroupRules(rulesRes.rule_versions || []);
      setGroupContributions(contribRes);
      setGroupPayouts(payoutsRes.payouts || []);
      setGroupPayoutsData(payoutsRes);
      setGroupDisputes(disputesRes || []);
      setReportData(repRes);
      setLotteryData(lotRes);
      setOverdueCases(Array.isArray(ovRes) ? ovRes : (ovRes?.results || []));
    } catch (err) {
      console.error('Error loading group sub data:', err);
    }
  };

  // Lottery Draw Handler
  const handleTriggerLotteryDraw = async () => {
    if (!selectedGroup) return;
    try {
      setDrawingLottery(true);
      setError('');
      const res = await api.triggerOrganizerLotteryDraw(selectedGroup.id);
      setSuccessMsg(res.message || 'Lottery draw executed successfully!');
      await loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 4500);
    } catch (err) {
      setError(err.message || 'Failed to execute lottery draw.');
    } finally {
      setDrawingLottery(false);
    }
  };

  // Start Next Cycle Handler
  const handleStartNextCycle = async () => {
    if (!selectedGroup) return;
    try {
      setStartingCycle(true);
      setError('');
      const res = await api.startOrganizerNextCycle(selectedGroup.id);
      setSuccessMsg(res.message || `Cycle #${res.cycle?.cycle_number || ''} initiated!`);
      await loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 4500);
    } catch (err) {
      setError(err.message || 'Failed to start next cycle.');
    } finally {
      setStartingCycle(false);
    }
  };

  // Overdue Evaluation Handler
  const handleEvaluateOverdue = async () => {
    if (!selectedGroup) return;
    try {
      setEvaluatingOverdue(true);
      setError('');
      const res = await api.evaluateOrganizerOverdueCases(selectedGroup.id);
      setSuccessMsg(res.message || 'Overdue contribution deadlines evaluated.');
      await loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to evaluate overdue cases.');
    } finally {
      setEvaluatingOverdue(false);
    }
  };

  // Open Resolution Modal (Dropdown 2: A, B, C)
  const handleOpenResolveModal = (c) => {
    setSelectedOverdueCase(c);
    setResolutionChoice('CONTINUE_WAITING');
    setWaitingDays(3);
    setWaitingReason(`Granted 3-day extension to clear ETB ${Number(c.amount_overdue || 0).toLocaleString()} balance.`);
    const half = Math.round(Number(c.amount_overdue || 0) / 2);
    setAgreementInstallments([
      { amount: String(half), due_date: new Date(Date.now() + 7 * 86400000).toISOString().split('T')[0] },
      { amount: String(Number(c.amount_overdue || 0) - half), due_date: new Date(Date.now() + 14 * 86400000).toISOString().split('T')[0] }
    ]);
    setReviewReason(`Unresolved contribution obligation exceeding grace period by ${c.days_overdue || 0} days.`);
    setReviewDecision('REPLACE_MEMBER');
    setReplacementUserId('');
    setShowResolveModal(true);
  };

  // Submit Resolution for Overdue Case
  const handleResolveOverdueSubmit = async (e) => {
    e.preventDefault();
    if (!selectedGroup || !selectedOverdueCase) return;
    try {
      setResolvingCase(true);
      setError('');
      const payload = { resolution_choice: resolutionChoice };
      if (resolutionChoice === 'CONTINUE_WAITING') {
        payload.follow_up_days = parseInt(waitingDays, 10);
        payload.reason = waitingReason;
      } else if (resolutionChoice === 'PAYMENT_AGREEMENT') {
        payload.reason = agreementReason;
        payload.total_amount = selectedOverdueCase.amount_overdue;
        payload.installments = agreementInstallments.map((inst, idx) => ({
          installment_number: idx + 1,
          amount: parseFloat(inst.amount),
          due_date: inst.due_date
        }));
      } else if (resolutionChoice === 'MEMBERSHIP_REVIEW') {
        payload.reason = reviewReason;
        payload.review_decision = reviewDecision;
        if (reviewDecision === 'REPLACE_MEMBER' && replacementUserId) {
          payload.replacement_user_id = replacementUserId;
        }
      }

      const res = await api.resolveOrganizerOverdueCase(selectedGroup.id, selectedOverdueCase.id, payload);
      setSuccessMsg(res.message || 'Overdue case resolution applied successfully!');
      setShowResolveModal(false);
      setSelectedOverdueCase(null);
      await loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 4500);
    } catch (err) {
      setError(err.message || 'Failed to apply resolution.');
    } finally {
      setResolvingCase(false);
    }
  };

  const handleGroupSelect = (group) => {
    setSelectedGroup(group);
    loadGroupSubData(group.id);
  };

  // Group Creation
  const handleCreateGroup = async (e) => {
    e.preventDefault();
    try {
      setError('');
      await api.createOrganizerGroup(createGroupForm);
      setSuccessMsg('Equb Group created successfully!');
      setShowCreateGroupModal(false);
      loadOverviewData();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to create group.');
    }
  };

  // Join Selected Group as Member
  const handleJoinSelectedGroupAsMember = async () => {
    if (!selectedGroup) return;
    try {
      setLoading(true);
      setError('');
      const res = await api.joinOrganizerGroupAsMember(selectedGroup.id);
      setSuccessMsg(res.message || 'You have successfully enrolled as a contributing member!');
      await loadGroupSubData(selectedGroup.id);
      await loadPersonalContributions();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to join group as member.');
    } finally {
      setLoading(false);
    }
  };

  // Lifecycle Action
  const handleLifecycleAction = async (groupId, action) => {
    try {
      setError('');
      await api.organizerGroupAction(groupId, action, `Action ${action} initiated by organizer.`);
      setSuccessMsg(`Group status updated (${action})`);
      loadOverviewData();
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Action failed.');
    }
  };

  // Member Invitation
  const handleInviteMember = async (e) => {
    e.preventDefault();
    if (!selectedGroup || !inviteEmail) return;
    try {
      setError('');
      const res = await api.createOrganizerGroupInvitation(selectedGroup.id, inviteEmail, 7);
      setInviteResult(res);
      setSuccessMsg(`Invitation generated for ${inviteEmail}`);
      setInviteEmail('');
      loadGroupSubData(selectedGroup.id);
    } catch (err) {
      setError(err.message || 'Failed to create invitation.');
    }
  };

  // Membership Request Action
  const handleMembershipRequestAction = async (membershipId, action) => {
    if (!selectedGroup) return;
    try {
      setError('');
      await api.organizerMembershipRequestAction(selectedGroup.id, membershipId, action);
      setSuccessMsg(`Membership request ${action}ed.`);
      loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Action failed.');
    }
  };

  // Treasurer Assignment
  const handleAssignTreasurer = async () => {
    if (!selectedGroup || !selectedTreasurerMemberId) return;
    try {
      setError('');
      await api.organizerTreasurerAction(selectedGroup.id, 'assign', selectedTreasurerMemberId);
      setSuccessMsg('Treasurer successfully assigned.');
      setShowAssignTreasurerModal(false);
      loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to assign treasurer.');
    }
  };

  const handleRevokeTreasurer = async () => {
    if (!selectedGroup) return;
    try {
      setError('');
      await api.organizerTreasurerAction(selectedGroup.id, 'revoke');
      setSuccessMsg('Treasurer role revoked.');
      loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to revoke treasurer.');
    }
  };

  // Payout Scheduling
  const handleSchedulePayout = async (e) => {
    e.preventDefault();
    if (!selectedGroup) return;
    try {
      setError('');
      await api.scheduleOrganizerGroupPayout(selectedGroup.id, payoutForm);
      setSuccessMsg('Payout scheduled successfully!');
      setShowSchedulePayoutModal(false);
      loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to schedule payout.');
    }
  };

  // Rule Proposal
  const handleProposeRule = async (e) => {
    e.preventDefault();
    if (!selectedGroup) return;
    try {
      setError('');
      await api.proposeOrganizerGroupRule(selectedGroup.id, ruleProposalForm);
      setSuccessMsg('New Rule charter version proposed to members!');
      setShowProposeRuleModal(false);
      loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to propose rule.');
    }
  };

  // Dispute Resolution
  const handleDisputeAction = async (disputeId, action, notes) => {
    if (!selectedGroup) return;
    try {
      setError('');
      await api.organizerDisputeAction(selectedGroup.id, disputeId, action, notes);
      setSuccessMsg(`Dispute action completed (${action})`);
      loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Dispute action failed.');
    }
  };

  // Support Ticket Submission
  const handleSupportTicketSubmit = async (e) => {
    e.preventDefault();
    try {
      setError('');
      await api.createOrganizerSupportTicket(supportTicketForm);
      setSuccessMsg('Support ticket submitted to Platform Admins.');
      setShowSupportTicketModal(false);
      setSupportTicketForm({ subject: '', category: 'TECHNICAL', message: '', group_id: '' });
      const tickets = await api.getOrganizerSupportTickets();
      setSupportTickets(tickets);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to submit ticket.');
    }
  };

  // Verification Submission
  const handleVerificationSubmit = async (e) => {
    e.preventDefault();
    try {
      setError('');
      await api.submitOrganizerVerification({
        category: 'ORGANIZER',
        submission_notes: verificationNotes
      });
      setSuccessMsg('Verification documents submitted. Pending Platform Super Admin review.');
      setShowVerificationModal(false);
      setVerificationNotes('');
      const verif = await api.getOrganizerVerification();
      setVerificationData(verif);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to submit verification.');
    }
  };

  // Select / Upgrade Plan via Chapa
  const handleUpgradePlan = async (planId) => {
    try {
      setError('');
      setLoading(true);
      const res = await api.payOrganizerSubscription({ plan_id: planId });
      if (res.is_free_starter) {
        setSuccessMsg(res.message || 'Starter plan activated with 0.00 ETB rent fee. Workspace unlocked!');
        await loadOverviewData();
        return;
      }
      if (res.checkout_url) {
        setSuccessMsg(`Chapa checkout session initiated! (Ref: ${res.tx_ref}). Redirecting to Chapa payment portal...`);
        // Navigate directly to the Chapa checkout interface
        window.location.href = res.checkout_url;
        return;
      }
      setSuccessMsg(res.message || 'Subscription payment initiated via Chapa.');
      await loadOverviewData();
    } catch (err) {
      setError(err.message || 'Failed to initiate Chapa payment for selected plan.');
    } finally {
      setLoading(false);
    }
  };

  // Renew Subscription
  const handleRenewSubscription = async () => {
    try {
      setError('');
      const planId = subscriptionData?.subscription?.plan?.id;
      const res = await api.payOrganizerSubscription({ plan_id: planId });
      if (res.is_free_starter) {
        setSuccessMsg(res.message || 'Starter plan renewed successfully.');
        await loadOverviewData();
      } else if (res.checkout_url) {
        setSuccessMsg('Redirecting to Chapa payment portal for subscription renewal...');
        window.location.href = res.checkout_url;
      }
    } catch (err) {
      setError(err.message || 'Failed to initiate subscription renewal via Chapa.');
    }
  };

  // Add Member Directly
  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!selectedGroup) return;
    try {
      setError('');
      const payload = {
        full_name: addMemberForm.full_name.trim(),
        email: addMemberForm.email.trim().toLowerCase(),
        phone_number: addMemberForm.phone_number.trim(),
        password_setup_method: addMemberForm.password_setup_method,
        initial_password: addMemberForm.initial_password.trim()
      };
      const res = await api.addOrganizerGroupMember(selectedGroup.id, payload);
      setAddMemberResult(res);
      setSuccessMsg(`Member ${payload.full_name} added to ${selectedGroup.name} successfully!`);
      loadGroupSubData(selectedGroup.id);
      loadOverviewData();
    } catch (err) {
      setError(err.message || 'Failed to add member to group.');
    }
  };

  // Open & Save Member Detail Modal
  const handleOpenMemberDetail = async (membershipId) => {
    if (!selectedGroup) return;
    try {
      setLoadingMemberDetail(true);
      setShowMemberDetailModal(true);
      const data = await api.getOrganizerGroupMemberDetail(selectedGroup.id, membershipId);
      setSelectedMemberDetail(data);
      setMemberDetailForm({
        full_name: data.user.full_name || '',
        phone_number: data.user.phone_number || '',
        payout_order_index: data.payout_order_index || 1,
        status: data.status || 'ACTIVE'
      });
    } catch (err) {
      setError(err.message || 'Failed to load member details.');
      setShowMemberDetailModal(false);
    } finally {
      setLoadingMemberDetail(false);
    }
  };

  const handleSaveMemberDetail = async (e) => {
    e.preventDefault();
    if (!selectedGroup || !selectedMemberDetail) return;
    try {
      setError('');
      await api.updateOrganizerGroupMember(selectedGroup.id, selectedMemberDetail.membership_id, memberDetailForm);
      setSuccessMsg(`Member details updated successfully.`);
      setShowMemberDetailModal(false);
      loadGroupSubData(selectedGroup.id);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to update member.');
    }
  };

  // Edit Group Modal
  const handleOpenEditGroup = (grp) => {
    setEditGroupForm({
      id: grp.id,
      name: grp.name || '',
      description: grp.description || '',
      group_purpose: grp.group_purpose || '',
      capacity: grp.capacity || 20
    });
    setShowEditGroupModal(true);
  };

  const handleSaveEditGroup = async (e) => {
    e.preventDefault();
    try {
      setError('');
      await api.updateOrganizerGroup(editGroupForm.id, {
        name: editGroupForm.name.trim(),
        description: editGroupForm.description.trim(),
        group_purpose: editGroupForm.group_purpose.trim(),
        capacity: Number(editGroupForm.capacity)
      });
      setSuccessMsg('Group details updated successfully.');
      setShowEditGroupModal(false);
      loadOverviewData();
      if (selectedGroup && selectedGroup.id === editGroupForm.id) {
        setSelectedGroup(prev => ({ ...prev, ...editGroupForm }));
      }
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to update group.');
    }
  };

  // Chapa Subaccount Link & Management
  const handleOpenSubaccountModal = async (group) => {
    setSelectedGroup(group);
    setShowSubaccountModal(true);
    setSubaccountLoading(true);
    setError('');
    try {
      const banksRes = await api.getSupportedBanks().catch(() => ({ banks: [] }));
      const remote = banksRes.banks || [];
      const seen = new Set();
      const combined = [];
      for (const b of [...remote, ...MASTER_ETHIOPIAN_BANKS]) {
        const key = b.name.toLowerCase().replace(/[^a-z0-9]/g, '');
        if (key && !seen.has(key)) {
          seen.add(key);
          combined.push(b);
        }
      }
      setSupportedBanks(combined);
      const banks = combined;

      const subRes = await api.getGroupSubaccount(group.id);
      setSubaccountInfo(subRes);

      const defaultBank = banks.find(b => String(b.id) === String(subRes.bank_code)) || banks[0];
      setSubaccountForm({
        bank_code: subRes.bank_code || (defaultBank ? String(defaultBank.id) : '946'),
        bank_name: subRes.bank_name || (defaultBank ? defaultBank.name : 'Commercial Bank of Ethiopia (CBE)'),
        account_name: subRes.bank_account_name || group.name,
        account_number: subRes.bank_account_number || '',
        business_name: group.name
      });
    } catch (err) {
      console.error('Error loading subaccount details:', err);
      setError(err.message || 'Failed to load subaccount details');
    } finally {
      setSubaccountLoading(false);
    }
  };

  const handleLinkSubaccount = async (e) => {
    if (e) e.preventDefault();
    if (!selectedGroup) return;
    if (!subaccountForm.bank_code || !subaccountForm.account_name || !subaccountForm.account_number) {
      setError('Please fill in bank, account holder name, and account number.');
      return;
    }
    setSubaccountLoading(true);
    setError('');
    try {
      const res = await api.linkGroupSubaccount(selectedGroup.id, {
        bank_code: subaccountForm.bank_code,
        bank_name: subaccountForm.bank_name,
        account_name: subaccountForm.account_name,
        account_number: subaccountForm.account_number,
        business_name: subaccountForm.business_name || selectedGroup.name
      });
      setSuccessMsg(res.message || 'Chapa Subaccount connected successfully!');
      setSubaccountInfo({
        ...subaccountInfo,
        has_subaccount: true,
        chapa_subaccount_id: res.subaccount_id,
        bank_name: subaccountForm.bank_name,
        bank_code: subaccountForm.bank_code,
        bank_account_name: subaccountForm.account_name,
        bank_account_number: subaccountForm.account_number
      });
      // Update groups list in state
      setGroups(prev => prev.map(g => g.id === selectedGroup.id ? {
        ...g,
        chapa_subaccount_id: res.subaccount_id,
        bank_code: subaccountForm.bank_code,
        bank_name: subaccountForm.bank_name,
        bank_account_name: subaccountForm.account_name,
        bank_account_number: subaccountForm.account_number
      } : g));
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to connect Chapa Subaccount.');
    } finally {
      setSubaccountLoading(false);
    }
  };

  // Save Settings
  const handlePhotoUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      setError('Profile image must be less than 2MB.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setSettingsForm(prev => ({ ...prev, avatar: reader.result }));
    };
    reader.readAsDataURL(file);
  };

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    try {
      setSettingsSaving(true);
      setError('');

      if (settingsForm.change_password) {
        if (!settingsForm.new_password || settingsForm.new_password.length < 8) {
          setError('New password must be at least 8 characters long.');
          setSettingsSaving(false);
          return;
        }
        if (settingsForm.new_password !== settingsForm.confirm_new_password) {
          setError('New password confirmation does not match.');
          setSettingsSaving(false);
          return;
        }
      }

      const payload = {
        full_name: settingsForm.full_name.trim(),
        phone_number: settingsForm.phone_number.trim(),
        preferred_language: settingsForm.preferred_language,
        avatar: settingsForm.avatar
      };
      if (settingsForm.change_password && settingsForm.new_password) {
        payload.current_password = settingsForm.current_password;
        payload.new_password = settingsForm.new_password;
      }

      const res = await api.updateProfile(payload);
      if (res?.user && setUser) {
        setUser(prev => ({ ...prev, ...res.user }));
      }
      if (refreshUser) refreshUser();
      setSuccessMsg('Organizer account preferences saved successfully.');
      setSettingsForm(prev => ({
        ...prev,
        current_password: '',
        new_password: '',
        confirm_new_password: '',
        change_password: false
      }));
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      setError(err.message || 'Failed to update account preferences.');
    } finally {
      setSettingsSaving(false);
    }
  };

  const overdueCount = (overdueCases || []).filter(c => c.status === 'PENDING' || c.status === 'GRACE_PERIOD_EXPIRED').length;

  // Navigation Items
  const navItems = [
    { id: 'dashboard', label: t('orgNavDashboard') || 'Dashboard', icon: LayoutDashboard },
    { id: 'groups', label: t('orgNavMyGroups') || 'My Groups', icon: Users },
    { id: 'members', label: t('orgNavMembers') || 'Members', icon: UserCheck },
    { id: 'contributions', label: t('orgNavContributions') || 'Contributions', icon: CircleDollarSign },
    { id: 'payouts', label: t('orgNavPayouts') || 'Payouts', icon: CreditCard },
    { id: 'lottery', label: t('orgNavLottery') || 'Lottery & Cycles', icon: Award },
    { id: 'overdue', label: t('orgNavOverdue') || 'Overdue Resolution', icon: AlertTriangle, badge: overdueCount },
    { id: 'subscriptions', label: t('orgNavSubscriptions') || 'Subscriptions', icon: Crown },
    { id: 'reports', label: t('orgNavReports') || 'Reports', icon: BarChart3 },
    { id: 'verification', label: t('orgNavVerification') || 'Verification Status', icon: ShieldCheck },
    { id: 'settings', label: t('orgNavSettings') || 'Settings', icon: Settings },
    { id: 'support', label: t('orgNavSupport') || 'Help & Support', icon: Headphones },
  ];

  const organizerName = dashData?.organizer_name || user?.full_name || 'Organizer';
  const kpis = dashData?.kpis || {
    total_groups: groups.length,
    groups_growth_sub: `${groups.length} active`,
    total_members: 0,
    members_growth_pct: 0,
    total_contributions_etb: 0,
    contributions_growth_pct: 0,
    pending_payout_etb: 0,
    next_payout_date: 'None scheduled'
  };

  const myGroupsSummary = dashData?.my_groups_summary || groups.slice(0, 3);
  const recentActivities = dashData?.recent_activities || [];
  const profileSub = dashData?.profile_subscription || {
    organizer_name: organizerName,
    title: 'Business Organizer',
    email: user?.email || 'selam@example.com',
    phone: user?.phone_number || '+251 911 123 456',
    current_plan: 'Growth Plan',
    status: 'Active',
    next_renewal: 'Jul 15, 2025'
  };

  const isStarterPlan = Boolean(
    dashData?.is_starter ||
    dashData?.assigned_plan_code === 'STARTER_EQUB' ||
    user?.organizer_profile_summary?.is_starter ||
    user?.organizer_profile_summary?.plan_code === 'STARTER_EQUB' ||
    subscriptionData?.subscription?.plan?.code === 'STARTER_EQUB' ||
    dashData?.assigned_plan_price === '0.00' ||
    dashData?.assigned_plan_price === 0 ||
    dashData?.payment_status === 'NOT_REQUIRED' ||
    dashData?.profile_subscription?.current_plan?.toLowerCase().includes('starter')
  );

  const isPaymentBlocked = !isStarterPlan && (
    dashData?.gate_reason === 'PAYMENT_REQUIRED' ||
    dashData?.payment_status === 'PAYMENT_REQUIRED' ||
    dashData?.payment_status === 'PAYMENT_PENDING' ||
    (dashData?.is_payment_blocked && dashData?.payment_status !== 'PAYMENT_CONFIRMED') ||
    (subscriptionData?.subscription?.status === 'PENDING_PAYMENT' && dashData?.payment_status !== 'PAYMENT_CONFIRMED') ||
    (!dashData && user?.organizer_profile_summary?.payment_status === 'PAYMENT_REQUIRED')
  );

  // When organizer has a paid plan with unpaid rent, dashboard access is strictly blocked
  if (isPaymentBlocked) {
    const unpaidInvoice = subscriptionData?.invoices?.find(inv => inv.status === 'UNPAID') || subscriptionData?.invoices?.[0];
    const planPrice = dashData?.assigned_plan_price || unpaidInvoice?.amount_etb || 600;
    const planName = dashData?.assigned_plan_name || 'Growth Organizer Plan';

    return (
      <div style={{
        minHeight: '100vh',
        backgroundColor: '#090e1a',
        color: '#f8fafc',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Top Navbar */}
        <header style={{
          padding: '1rem 2rem',
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.7)',
          backdropFilter: 'blur(8px)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #10b981 0%, #f59e0b 50%, #ef4444 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)'
            }}>
              <Users size={20} color="#ffffff" />
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: '1.05rem', color: '#ffffff', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                Digital Equb <span style={{ color: '#10b981' }}>Ethiopia</span>
                <span className="badge badge-yellow" style={{ fontSize: '0.65rem' }}>RENT PAYMENT REQUIRED</span>
              </div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                Multi-Tenant Equb Financial SaaS
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{ textAlign: 'right', fontSize: '0.8rem' }}>
              <div style={{ fontWeight: 600, color: '#f1f5f9' }}>{organizerName}</div>
              <div style={{ color: '#94a3b8', fontSize: '0.72rem' }}>{user?.email}</div>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={logout}
              style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.4rem', color: '#f87171', borderColor: 'rgba(239,68,68,0.3)' }}
            >
              <LogOut size={15} /> Sign Out
            </button>
          </div>
        </header>

        {/* Alerts */}
        {error && (
          <div style={{ maxWidth: '850px', margin: '1.5rem auto 0', width: '92%', padding: '0.85rem 1.25rem', background: '#451a1a', border: '1px solid #7f1d1d', borderRadius: '10px', color: '#fca5a5', display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.875rem' }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}
        {successMsg && (
          <div style={{ maxWidth: '850px', margin: '1.5rem auto 0', width: '92%', padding: '0.85rem 1.25rem', background: '#064e3b', border: '1px solid #065f46', borderRadius: '10px', color: '#6ee7b7', display: 'flex', alignItems: 'center', gap: '0.6rem', fontSize: '0.875rem' }}>
            <CheckCircle2 size={18} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Main Content Area */}
        <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem 1.5rem' }}>
          <div style={{
            maxWidth: '850px',
            width: '100%',
            backgroundColor: '#0f172a',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '16px',
            overflow: 'hidden',
            boxShadow: '0 20px 40px rgba(0,0,0,0.45)'
          }}>
            {/* Hero Banner inside Card */}
            <div style={{
              padding: '2rem 2.5rem 1.5rem',
              background: 'linear-gradient(180deg, rgba(37, 99, 235, 0.15) 0%, rgba(15, 23, 42, 0) 100%)',
              borderBottom: '1px solid rgba(255,255,255,0.06)'
            }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', padding: '0.35rem 0.75rem', borderRadius: '999px', background: 'rgba(217, 119, 6, 0.2)', border: '1px solid rgba(217, 119, 6, 0.4)', color: '#fbbf24', fontSize: '0.75rem', fontWeight: 700, marginBottom: '1rem' }}>
                <ShieldAlert size={14} /> DASHBOARD ACCESS LOCKED — SUBSCRIPTION RENT REQUIRED
              </div>
              <h1 style={{ fontSize: '1.65rem', fontWeight: 800, color: '#ffffff', marginBottom: '0.5rem', letterSpacing: '-0.02em' }}>
                Pay Monthly SaaS Rent to Activate Your Workspace
              </h1>
              <p style={{ fontSize: '0.9rem', color: '#94a3b8', lineHeight: 1.6, margin: 0 }}>
                Welcome to Digital Equb Ethiopia. Your Organizer account was registered by the Platform Super Admin. Because your account is enrolled in a paid professional tier, your monthly subscription rent must be paid to unlock your Organizer Dashboard and begin creating Equb groups.
              </p>

              {/* Starter Equb Policy Note */}
              <div style={{
                marginTop: '1.25rem',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                background: 'rgba(255,255,255,0.03)',
                border: '1px dashed rgba(255,255,255,0.12)',
                fontSize: '0.8rem',
                color: '#cbd5e1',
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem'
              }}>
                <Crown size={16} color="#fbbf24" style={{ flexShrink: 0 }} />
                <span>
                  <strong>Starter Equb Community Policy:</strong> Starter Equb accounts are free of charge and do not require rent. Your organization is enrolled in the <strong>{planName}</strong> tier, which requires payment confirmation.
                </span>
              </div>
            </div>

            {/* Split Details & Payment Form */}
            <div style={{ padding: '2rem 2.5rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '2rem' }}>
              {/* Left Column: Plan & Invoice Summary */}
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Subscription Rent Details
                </h3>

                <div style={{
                  padding: '1.25rem',
                  borderRadius: '12px',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  marginBottom: '1rem'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Enrolled Plan</span>
                    <span style={{ fontWeight: 700, color: '#38bdf8', fontSize: '0.95rem' }}>{planName}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Monthly Rent</span>
                    <span style={{ fontWeight: 800, color: '#10b981', fontSize: '1.15rem' }}>ETB {Number(planPrice).toLocaleString()}.00</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Max Concurrent Groups</span>
                    <span style={{ fontWeight: 600, color: '#f1f5f9', fontSize: '0.85rem' }}>{dashData?.profile_subscription?.max_groups || 5} Groups</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Invoice Reference</span>
                    <span style={{ fontFamily: 'monospace', fontWeight: 600, color: '#f59e0b', fontSize: '0.85rem' }}>
                      {unpaidInvoice?.invoice_number || 'INV-CURRENT'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Invoice Status</span>
                    <span style={{ padding: '0.2rem 0.6rem', borderRadius: '4px', background: 'rgba(239,68,68,0.2)', color: '#f87171', fontSize: '0.72rem', fontWeight: 700 }}>
                      UNPAID / RENT DUE
                    </span>
                  </div>
                </div>

                {/* Financial Isolation Guarantee */}
                <div style={{
                  padding: '0.85rem 1rem',
                  borderRadius: '10px',
                  background: 'rgba(16, 185, 129, 0.05)',
                  border: '1px solid rgba(16, 185, 129, 0.15)',
                  fontSize: '0.75rem',
                  color: '#94a3b8',
                  lineHeight: 1.5
                }}>
                  <div style={{ fontWeight: 700, color: '#10b981', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <ShieldCheck size={14} /> Strict Financial Segregation
                  </div>
                  SaaS subscription rent payments are credited directly to software platform operations and are strictly isolated from rotating Equb communal savings.
                </div>
              </div>

              {/* Right Column: Interactive Payment Form */}
              <div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f1f5f9', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Pay Via Chapa Payment Gateway
                </h3>

                <form onSubmit={handlePaySubscription}>
                  {/* Official Gateway Badge */}
                  <div style={{
                    padding: '1rem',
                    borderRadius: '10px',
                    border: '2px solid #10b981',
                    background: 'rgba(16, 185, 129, 0.1)',
                    marginBottom: '1.25rem'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ fontWeight: 800, fontSize: '0.95rem', color: '#10b981' }}>
                        Chapa Payment Gateway
                      </div>
                      <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>OFFICIAL GATEWAY</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.35rem', lineHeight: 1.5 }}>
                      Direct integration with Chapa (Ethiopian debit cards, Telebirr, CBE Birr, and mobile money). You will be securely redirected to the official Chapa checkout page.
                    </div>
                  </div>

                  {/* Merchant Account Settlement Note */}
                  <div style={{
                    padding: '0.75rem 1rem',
                    borderRadius: '8px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    fontSize: '0.75rem',
                    color: '#94a3b8',
                    marginBottom: '1.5rem',
                    lineHeight: 1.5
                  }}>
                    <div style={{ color: '#cbd5e1', fontWeight: 600, marginBottom: '0.2rem' }}>
                      Settlement Notice:
                    </div>
                    Subscription payments settle into the platform owner's verified Chapa merchant business account. Never deducted from Equb group pooled savings.
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={payingSubscription}
                    style={{
                      width: '100%',
                      padding: '0.85rem',
                      borderRadius: '10px',
                      background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                      color: '#ffffff',
                      border: 'none',
                      fontSize: '0.95rem',
                      fontWeight: 700,
                      cursor: payingSubscription ? 'not-allowed' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '0.6rem',
                      boxShadow: '0 4px 14px rgba(16, 185, 129, 0.4)',
                      opacity: payingSubscription ? 0.7 : 1
                    }}
                  >
                    {payingSubscription ? (
                      <>
                        <div style={{ width: '16px', height: '16px', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
                        <span>Connecting to Chapa Gateway...</span>
                      </>
                    ) : (
                      <>
                        <CreditCard size={18} />
                        <span>Pay Rent via Chapa — ETB {Number(planPrice).toLocaleString()}.00</span>
                      </>
                    )}
                  </button>
                </form>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="org-container" data-theme={effectiveTheme}>
      {/* Mobile Overlay */}
      <div
        className={`org-sidebar-overlay ${sidebarOpen ? 'active' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* 1. Left Dark Navy Sidebar Navigation */}
      <aside className={`org-sidebar ${sidebarOpen ? 'open' : 'closed collapsed'}`}>
        {/* Brand Logo Header */}
        <div className="org-logo-container" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 0, flex: 1 }}>
            <div className="org-logo-emblem">
              <Users size={20} />
            </div>
            <div className="org-brand-text">
              <span className="org-brand-title">Digital Equb</span>
              <span className="org-brand-country">Ethiopia</span>
            </div>
          </div>
          <button
            type="button"
            className="org-sidebar-close-btn"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close Navigation Sidebar"
            title="Close Sidebar"
          >
            <X size={18} />
          </button>
        </div>

        {/* 12 Navigation Items */}
        <nav className="org-nav-menu">
          {navItems.map((item) => {
            const IconComponent = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`org-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => {
                  setActiveTab(item.id);
                  if (typeof window !== 'undefined' && window.innerWidth <= 1024) {
                    setSidebarOpen(false);
                  }
                }}
              >
                <IconComponent size={18} />
                <span>{item.label}</span>
                {item.id === 'verification' && verificationData?.organizer_identity?.status === 'PENDING' && (
                  <span className="org-nav-badge">1</span>
                )}
                {Boolean(item.badge) && (
                  <span className="org-nav-badge" style={{ backgroundColor: '#ef4444', color: '#ffffff', fontWeight: 700, padding: '0.1rem 0.45rem', borderRadius: '10px' }}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom CTA Banner Card */}
        <div className="org-sidebar-cta">
          <div className="org-cta-card">
            <div className="org-cta-icon-circle">
              <Crown size={20} />
            </div>
            <div className="org-cta-title">{t('upgradeYourPlan') || 'Upgrade Your Plan'}</div>
            <div className="org-cta-subtitle">
              {t('upgradeSubtext') || 'Get more groups and advanced features.'}
            </div>
            <button
              type="button"
              className="org-cta-btn"
              onClick={() => {
                setActiveTab('subscriptions');
                if (typeof window !== 'undefined' && window.innerWidth <= 1024) {
                  setSidebarOpen(false);
                }
              }}
            >
              {t('upgradePlanBtn') || 'Upgrade Plan'}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className={`org-main-wrapper ${!sidebarOpen ? 'sidebar-collapsed' : ''}`}>
        {/* 2. Top Navigation Bar */}
        <header className="org-topbar">
          <div className="org-topbar-left">
            <button
              type="button"
              className="org-menu-btn"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle Navigation Sidebar"
              title="Toggle Sidebar"
            >
              <Menu size={20} />
            </button>
            <button
              type="button"
              className="org-refresh-btn"
              onClick={handleRefreshAll}
              disabled={refreshing}
              title="Refresh all Equb data"
              aria-label="Refresh Dashboard Data"
            >
              <RefreshCw size={16} className={refreshing ? 'org-spin' : ''} />
              <span className="org-refresh-text">{refreshing ? (t('refreshing') || 'Refreshing...') : (t('refresh') || 'Refresh')}</span>
            </button>
          </div>

          <div className="org-topbar-right">
            {/* Theme & 4-Language Dropdowns */}
            <HeaderControls />

            {/* Real Notification Center */}
            <NotificationCenter />

            {/* Profile Dropdown Menu */}
            <div className="org-user-pill" onClick={() => setUserDropdownOpen(!userDropdownOpen)}>
              <div className="org-user-avatar-initials" style={{ overflow: 'hidden' }}>
                {user?.avatar ? (
                  <img src={user.avatar} alt="Avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  organizerName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'OR'
                )}
              </div>
              <div className="org-user-info">
                <span className="org-user-name">{organizerName}</span>
                <span className="org-user-role">{t('roleOrganizer') || 'Organizer'} ▾</span>
              </div>

              {userDropdownOpen && (
                <div className="org-dropdown-menu">
                  <div style={{ padding: '0.4rem 0.75rem', borderBottom: '1px solid #f1f5f9', fontSize: '0.75rem', color: '#64748b' }}>
                    Signed in as <strong>{user?.email || organizerName}</strong>
                  </div>
                  <button
                    type="button"
                    className="org-dropdown-item"
                    onClick={() => { setActiveTab('settings'); setUserDropdownOpen(false); }}
                  >
                    <Settings size={16} /> Profile & Settings
                  </button>
                  <button
                    type="button"
                    className="org-dropdown-item"
                    style={{ color: '#ef4444' }}
                    onClick={logout}
                  >
                    <LogOut size={16} /> Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Alerts & Notifications */}
        {error && (
          <div style={{ margin: '1rem 1.5rem 0', padding: '0.75rem 1rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}
        {successMsg && (
          <div style={{ margin: '1rem 1.5rem 0', padding: '0.75rem 1rem', background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: '8px', color: '#047857', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
            <CheckCircle2 size={18} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Organizer Verification & Subscription Gate Banner */}
        {dashData?.gate_blocked && (
          <div style={{
            margin: '1rem 1.5rem 0',
            padding: '1rem 1.25rem',
            background: dashData.gate_reason === 'PAYMENT_REQUIRED' ? '#fffbeb' : '#eff6ff',
            border: `1px solid ${dashData.gate_reason === 'PAYMENT_REQUIRED' ? '#fde68a' : '#bfdbfe'}`,
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '1rem',
            boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
          }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: dashData.gate_reason === 'PAYMENT_REQUIRED' ? '#fef3c7' : '#dbeafe',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              <ShieldAlert size={20} color={dashData.gate_reason === 'PAYMENT_REQUIRED' ? '#d97706' : '#2563eb'} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: '0.95rem', color: dashData.gate_reason === 'PAYMENT_REQUIRED' ? '#92400e' : '#1e40af', marginBottom: '0.25rem' }}>
                {dashData.gate_reason === 'PAYMENT_REQUIRED' ? 'Subscription Payment Required' : 'Organizer Verification In Progress'}
              </div>
              <div style={{ fontSize: '0.85rem', color: dashData.gate_reason === 'PAYMENT_REQUIRED' ? '#b45309' : '#1e3a8a', lineHeight: 1.5 }}>
                {dashData.gate_message || 'Your organizer account governance check is active.'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginTop: '0.6rem' }}>
                {dashData.gate_reason === 'PAYMENT_REQUIRED' ? (
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ padding: '0.35rem 0.85rem', fontSize: '0.8rem', backgroundColor: '#d97706', borderColor: '#d97706', color: '#fff' }}
                    onClick={() => setActiveTab('subscriptions')}
                  >
                    Pay Subscription ({dashData.assigned_plan_price || 600} ETB)
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ padding: '0.35rem 0.85rem', fontSize: '0.8rem' }}
                    onClick={() => setActiveTab('verification')}
                  >
                    View Verification Status
                  </button>
                )}
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  Verification Status: <strong>{dashData.verification_status || 'PENDING'}</strong> • Payment Status: <strong>{dashData.payment_status || 'PAYMENT_REQUIRED'}</strong>
                </span>
              </div>
            </div>
          </div>
        )}

        {/* 3. Main Viewport Content by Active Tab */}
        <main className="org-viewport">
          {/* TAB 1: DASHBOARD OVERVIEW (Pixel-Perfect Matching Mockup) */}
          {activeTab === 'dashboard' && (
            <div>
              {/* Panoramic Welcome Hero Banner */}
              <div className="org-welcome-hero">
                <div className="org-hero-skyline" />
                <h1 className="org-hero-title">
                  {t('welcomeBack') || 'Welcome back'}, {organizerName}!
                </h1>
                <p className="org-hero-subtitle">
                  {t('manageYourGroups') || 'Manage your Equb groups and track your activities.'}
                </p>
              </div>

              {/* 4 Core KPI Cards Grid */}
              <div className="org-kpi-grid">
                {/* 1. Total Groups */}
                <div className="org-kpi-card">
                  <div className="org-kpi-icon-badge org-kpi-blue">
                    <Users size={24} />
                  </div>
                  <div className="org-kpi-content">
                    <div className="org-kpi-value">{kpis.total_groups}</div>
                    <div className="org-kpi-label">{t('totalGroupsCard') || 'Total Groups'}</div>
                    <div className="org-kpi-sub org-sub-green">
                      <span>↑ {kpis.groups_growth_sub || '1 new'}</span>
                    </div>
                  </div>
                </div>

                {/* 2. Total Members */}
                <div className="org-kpi-card">
                  <div className="org-kpi-icon-badge org-kpi-green">
                    <UserCheck size={24} />
                  </div>
                  <div className="org-kpi-content">
                    <div className="org-kpi-value">{kpis.total_members}</div>
                    <div className="org-kpi-label">{t('totalMembersCard') || 'Total Members'}</div>
                    <div className="org-kpi-sub org-sub-green">
                      <span>↑ {kpis.members_growth_pct || 5}%</span>
                    </div>
                  </div>
                </div>

                {/* 3. Total Contributions */}
                <div className="org-kpi-card">
                  <div className="org-kpi-icon-badge org-kpi-purple">
                    <CircleDollarSign size={24} />
                  </div>
                  <div className="org-kpi-content">
                    <div className="org-kpi-value">
                      ETB {Number(kpis.total_contributions_etb ?? 0).toLocaleString()}
                    </div>
                    <div className="org-kpi-label">{t('totalContributionsCard') || 'Total Contributions'}</div>
                    <div className="org-kpi-sub org-sub-green">
                      <span>↑ {kpis.contributions_growth_pct || 0}%</span>
                    </div>
                  </div>
                </div>

                {/* 4. Pending Payout */}
                <div className="org-kpi-card">
                  <div className="org-kpi-icon-badge org-kpi-orange">
                    <CreditCard size={24} />
                  </div>
                  <div className="org-kpi-content">
                    <div className="org-kpi-value">
                      ETB {Number(kpis.pending_payout_etb ?? 0).toLocaleString()}
                    </div>
                    <div className="org-kpi-label">{t('pendingPayoutCard') || 'Pending Payout'}</div>
                    <div className="org-kpi-sub org-sub-muted">
                      <Clock size={12} />
                      <span>{t('nextLabel') || 'Next'}: {kpis.next_payout_date || 'None scheduled'}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Middle Row: Analytics Chart & Profile / Subscription */}
              <div className="org-middle-row">
                {/* Left Card: Your Groups Performance Line Chart */}
                <div className="org-card">
                  <div className="org-card-header">
                    <div className="org-card-title-group">
                      <BarChart3 size={20} color="#2563eb" />
                      <span>{t('yourGroupsPerformance') || 'Your Groups Performance'}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <select className="org-select" style={{ fontSize: '0.78rem', padding: '0.25rem 0.5rem' }}>
                        <option>{t('last6Months') || 'Last 6 Months'}</option>
                        <option>Last 3 Months</option>
                        <option>This Year</option>
                      </select>
                    </div>
                  </div>

                  <div className="org-chart-legend">
                    <div>
                      <span className="org-legend-dot" style={{ backgroundColor: '#2563eb' }} />{' '}
                      <span>{t('groupsSeries') || 'Groups'}</span>
                    </div>
                    <div>
                      <span className="org-legend-dot" style={{ backgroundColor: '#10b981' }} />{' '}
                      <span>{t('membersSeries') || 'Members'}</span>
                    </div>
                  </div>

                  {/* High Quality Inline SVG Multi-Line Chart */}
                  <div className="org-chart-container">
                    <svg viewBox="0 0 500 180" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
                      {/* Grid Lines */}
                      <line x1="40" y1="20" x2="480" y2="20" stroke="#f1f5f9" strokeWidth="1" />
                      <line x1="40" y1="55" x2="480" y2="55" stroke="#f1f5f9" strokeWidth="1" />
                      <line x1="40" y1="90" x2="480" y2="90" stroke="#f1f5f9" strokeWidth="1" />
                      <line x1="40" y1="125" x2="480" y2="125" stroke="#f1f5f9" strokeWidth="1" />
                      <line x1="40" y1="160" x2="480" y2="160" stroke="#e2e8f0" strokeWidth="1" />

                      {/* Y-Axis Labels */}
                      <text x="25" y="24" fontSize="10" fill="#94a3b8" textAnchor="end">4</text>
                      <text x="25" y="59" fontSize="10" fill="#94a3b8" textAnchor="end">3</text>
                      <text x="25" y="94" fontSize="10" fill="#94a3b8" textAnchor="end">2</text>
                      <text x="25" y="129" fontSize="10" fill="#94a3b8" textAnchor="end">1</text>
                      <text x="25" y="164" fontSize="10" fill="#94a3b8" textAnchor="end">0</text>

                      {/* Area Fill for Groups Curve */}
                      <defs>
                        <linearGradient id="blueGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#2563eb" stopOpacity="0.25" />
                          <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
                        </linearGradient>
                        <linearGradient id="greenGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#10b981" stopOpacity="0.2" />
                          <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                        </linearGradient>
                      </defs>

                      <polygon
                        points="60,125 140,115 220,90 300,90 380,55 460,55 460,160 60,160"
                        fill="url(#blueGradient)"
                      />

                      {/* Blue Line: Groups */}
                      <polyline
                        fill="none"
                        stroke="#2563eb"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        points="60,125 140,115 220,90 300,90 380,55 460,55"
                      />

                      {/* Green Line: Members */}
                      <polyline
                        fill="none"
                        stroke="#10b981"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeDasharray="4 2"
                        points="60,155 140,140 220,115 300,105 380,85 460,65"
                      />

                      {/* Data Markers & Values */}
                      {/* Jan */}
                      <circle cx="60" cy="125" r="4" fill="#2563eb" />
                      <text x="60" y="117" fontSize="9" fill="#2563eb" textAnchor="middle" fontWeight="bold">1</text>
                      <circle cx="60" cy="155" r="3" fill="#10b981" />
                      <text x="60" y="175" fontSize="10" fill="#64748b" textAnchor="middle">Jan</text>

                      {/* Feb */}
                      <circle cx="140" cy="115" r="4" fill="#2563eb" />
                      <text x="140" y="107" fontSize="9" fill="#2563eb" textAnchor="middle" fontWeight="bold">1</text>
                      <circle cx="140" cy="140" r="3" fill="#10b981" />
                      <text x="140" y="175" fontSize="10" fill="#64748b" textAnchor="middle">Feb</text>

                      {/* Mar */}
                      <circle cx="220" cy="90" r="4" fill="#2563eb" />
                      <text x="220" y="82" fontSize="9" fill="#2563eb" textAnchor="middle" fontWeight="bold">2</text>
                      <circle cx="220" cy="115" r="3" fill="#10b981" />
                      <text x="220" y="127" fontSize="8" fill="#10b981" textAnchor="middle">75</text>
                      <text x="220" y="175" fontSize="10" fill="#64748b" textAnchor="middle">Mar</text>

                      {/* Apr */}
                      <circle cx="300" cy="90" r="4" fill="#2563eb" />
                      <text x="300" y="82" fontSize="9" fill="#2563eb" textAnchor="middle" fontWeight="bold">2</text>
                      <circle cx="300" cy="105" r="3" fill="#10b981" />
                      <text x="300" y="175" fontSize="10" fill="#64748b" textAnchor="middle">Apr</text>

                      {/* May */}
                      <circle cx="380" cy="55" r="4" fill="#2563eb" />
                      <text x="380" y="47" fontSize="9" fill="#2563eb" textAnchor="middle" fontWeight="bold">3</text>
                      <circle cx="380" cy="85" r="3" fill="#10b981" />
                      <text x="380" y="97" fontSize="8" fill="#10b981" textAnchor="middle">120</text>
                      <text x="380" y="175" fontSize="10" fill="#64748b" textAnchor="middle">May</text>

                      {/* Jun */}
                      <circle cx="460" cy="55" r="4" fill="#2563eb" />
                      <text x="460" y="47" fontSize="9" fill="#2563eb" textAnchor="middle" fontWeight="bold">3</text>
                      <circle cx="460" cy="65" r="3" fill="#10b981" />
                      <text x="460" y="77" fontSize="8" fill="#10b981" textAnchor="middle">147</text>
                      <text x="460" y="175" fontSize="10" fill="#64748b" textAnchor="middle">Jun</text>
                    </svg>
                  </div>
                </div>

                {/* Right Card: Your Profile & Subscription */}
                <div className="org-card">
                  <div className="org-card-header">
                    <div className="org-card-title-group">
                      <Crown size={20} color="#2563eb" />
                      <span>{t('yourProfileSubscription') || 'Your Profile & Subscription'}</span>
                    </div>
                    <span className="org-badge org-badge-green">Active</span>
                  </div>

                  <div className="org-profile-sub-body">
                    {/* User Snippet */}
                    <div className="org-profile-snippet">
                      <div className="org-profile-avatar-circle">
                        {organizerName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'OR'}
                      </div>
                      <div className="org-profile-details">
                        <span className="org-profile-name">{organizerName}</span>
                        <span className="org-profile-role">{t('businessOrganizer') || 'Business Organizer'}</span>
                        <span className="org-profile-contact">
                          ✉ {profileSub.email || 'selam@example.com'}
                        </span>
                        <span className="org-profile-contact">
                          📞 {profileSub.phone || '+251 911 123 456'}
                        </span>
                      </div>
                    </div>

                    {/* Plan & Renewal Box */}
                    <div className="org-plan-card-inner">
                      <div className="org-plan-info">
                        <span className="org-plan-lbl">{t('currentPlan') || 'Current Plan'}</span>
                        <span className="org-plan-val">{profileSub.current_plan || 'Growth Plan'}</span>
                        <span
                          className="org-view-all-link"
                          onClick={() => setActiveTab('subscriptions')}
                        >
                          {t('viewDetails') || 'View Details →'}
                        </span>
                      </div>

                      <div className="org-renewal-box">
                        <Calendar size={18} color="#047857" style={{ marginBottom: '4px' }} />
                        <span className="org-renewal-lbl">{t('nextRenewal') || 'Next Renewal'}</span>
                        <span className="org-renewal-val">{profileSub.next_renewal || 'Jul 15, 2025'}</span>
                        <button
                          type="button"
                          className="org-btn-manage-sub"
                          onClick={() => setActiveTab('subscriptions')}
                        >
                          {t('manageSubscription') || 'Manage Subscription'}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Bottom Row: My Groups Summary Table & Recent Activity Feed */}
              <div className="org-bottom-row">
                {/* Left Card: My Groups Summary Table */}
                <div className="org-card">
                  <div className="org-card-header">
                    <div className="org-card-title-group">
                      <Users size={20} color="#2563eb" />
                      <span>{t('myGroupsTableTitle') || 'My Groups'}</span>
                    </div>
                    <span
                      className="org-view-all-link"
                      onClick={() => setActiveTab('groups')}
                    >
                      {t('viewAllLink') || 'View All →'}
                    </span>
                  </div>

                  <div className="org-table-responsive">
                    <table className="org-table">
                      <thead>
                        <tr>
                          <th>{t('groupNameCol') || 'Group Name'}</th>
                          <th>{t('membersCol') || 'Members'}</th>
                          <th>{t('contributionCol') || 'Contribution'}</th>
                          <th>{t('nextContributionCol') || 'Next Contribution'}</th>
                          <th>{t('statusCol') || 'Status'}</th>
                          <th>{t('actionsCol') || 'Actions'}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {myGroupsSummary.length === 0 ? (
                          <tr>
                            <td colSpan={6} style={{ textAlign: 'center', padding: '2.5rem 1rem', color: '#94a3b8' }}>
                              <Users size={28} color="#cbd5e1" style={{ marginBottom: '0.4rem', display: 'inline-block' }} />
                              <div>No groups created yet. Click "Create Group" in My Groups to start your first Equb!</div>
                            </td>
                          </tr>
                        ) : (
                          myGroupsSummary.map((grp) => (
                            <tr key={grp.id}>
                              <td>
                                <div className="org-group-name-cell">
                                  {grp.name?.includes('Family') ? (
                                    <Home size={18} color="#2563eb" />
                                  ) : grp.name?.includes('Business') ? (
                                    <Briefcase size={18} color="#2563eb" />
                                  ) : (
                                    <Users size={18} color="#2563eb" />
                                  )}
                                  <span>{grp.name}</span>
                                </div>
                              </td>
                              <td style={{ fontWeight: 600 }}>{grp.members_count}</td>
                              <td style={{ fontWeight: 600 }}>
                                ETB {Number(grp.contribution_amount).toLocaleString()}
                              </td>
                              <td style={{ color: '#475569' }}>
                                {grp.next_contribution_date || 'None scheduled'}
                              </td>
                              <td>
                                <span className="org-badge org-badge-green">
                                  {grp.status === 'ACTIVE' ? 'Active' : grp.status}
                                </span>
                              </td>
                              <td>
                                <button
                                  type="button"
                                  className="org-btn-view-pill"
                                  onClick={() => {
                                    handleGroupSelect(grp);
                                    setShowGroupDetailsModal(true);
                                  }}
                                >
                                  {t('viewBtn') || 'View'}
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Right Card: Recent Activity Feed */}
                <div className="org-card">
                  <div className="org-card-header">
                    <div className="org-card-title-group">
                      <Clock size={20} color="#2563eb" />
                      <span>{t('recentActivityTitle') || 'Recent Activity'}</span>
                    </div>
                    <span
                      className="org-view-all-link"
                      onClick={() => setActiveTab('groups')}
                    >
                      {t('viewAllLink') || 'View All →'}
                    </span>
                  </div>

                  <div className="org-activity-list">
                    {recentActivities.length === 0 ? (
                      <div style={{ padding: '2.5rem 1rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.85rem' }}>
                        <div>No recent activity recorded yet. Group events and payments will show here.</div>
                      </div>
                    ) : (
                      recentActivities.map((act) => (
                        <div key={act.id} className="org-activity-item">
                          <div
                            className="org-act-icon"
                            style={{
                              backgroundColor:
                                act.type === 'contribution_received'
                                  ? '#ecfdf5'
                                  : act.type === 'member_joined'
                                  ? '#eff6ff'
                                  : act.type === 'payout_scheduled'
                                  ? '#f5f3ff'
                                  : '#fffbeb',
                              color:
                                act.type === 'contribution_received'
                                  ? '#10b981'
                                  : act.type === 'member_joined'
                                  ? '#2563eb'
                                  : act.type === 'payout_scheduled'
                                  ? '#8b5cf6'
                                  : '#f59e0b',
                            }}
                          >
                            {act.type === 'contribution_received' && <CheckCircle2 size={16} />}
                            {act.type === 'member_joined' && <Users size={16} />}
                            {act.type === 'payout_scheduled' && <CreditCard size={16} />}
                            {act.type === 'group_updated' && <AlertCircle size={16} />}
                          </div>
                          <div className="org-act-content">
                            <div className="org-act-title">{act.title}</div>
                            <div className="org-act-desc">{act.description}</div>
                          </div>
                          <div className="org-act-time">{act.timestamp_human}</div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: MY GROUPS MODULE */}
          {activeTab === 'groups' && (
            <div className="org-card">
              <div className="org-card-header">
                <div>
                  <h2 className="org-card-title">
                    {t('orgNavMyGroups') || 'My Groups'}
                  </h2>
                  <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                    Manage and configure your Equb groups, review members, rules, and lifecycles.
                  </p>
                </div>
                <button
                  type="button"
                  className="org-btn-primary"
                  onClick={() => setShowCreateGroupModal(true)}
                  style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  <Plus size={16} /> {t('orgCreateGroup') || 'Create Equb Group'}
                </button>
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
                <input
                  type="text"
                  placeholder="Search groups..."
                  className="org-input"
                  style={{ maxWidth: '300px' }}
                />
              </div>

              <table className="org-table">
                <thead>
                  <tr>
                    <th>Group Name</th>
                    <th>Category / Purpose</th>
                    <th>Contribution (ETB)</th>
                    <th>Frequency</th>
                    <th>Members</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((grp) => (
                    <tr key={grp.id}>
                      <td style={{ fontWeight: 700 }}>{grp.name}</td>
                      <td style={{ color: '#64748b' }}>{grp.group_purpose || 'General Savings'}</td>
                      <td style={{ fontWeight: 600 }}>ETB {Number(grp.contribution_amount).toLocaleString()}</td>
                      <td>{grp.contribution_frequency}</td>
                      <td>{grp.members_count || grp.capacity}</td>
                      <td>
                        <span className={`org-badge ${grp.status === 'ACTIVE' ? 'org-badge-green' : 'org-badge-orange'}`}>
                          {grp.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            className="org-btn-view-pill"
                            onClick={() => {
                              handleGroupSelect(grp);
                              setShowGroupDetailsModal(true);
                            }}
                          >
                            Details
                          </button>
                          <button
                            type="button"
                            className="org-btn-view-pill"
                            style={{
                              color: grp.chapa_subaccount_id ? '#047857' : '#2563eb',
                              borderColor: grp.chapa_subaccount_id ? '#a7f3d0' : '#bfdbfe',
                              background: grp.chapa_subaccount_id ? '#ecfdf5' : '#eff6ff',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '0.25rem'
                            }}
                            onClick={() => handleOpenSubaccountModal(grp)}
                            title="Configure Chapa Subaccount for direct member payment routing"
                          >
                            <Landmark size={12} />
                            {grp.chapa_subaccount_id ? 'Bank (Linked)' : 'Link Bank'}
                          </button>
                          <button
                            type="button"
                            className="org-btn-view-pill"
                            style={{ color: '#2563eb' }}
                            onClick={() => handleOpenEditGroup(grp)}
                          >
                            Edit
                          </button>
                          {grp.status === 'ACTIVE' ? (
                            <button
                              type="button"
                              className="org-btn-view-pill"
                              style={{ color: '#b45309' }}
                              onClick={() => handleLifecycleAction(grp.id, 'pause')}
                            >
                              Pause
                            </button>
                          ) : grp.status === 'SUSPENDED' ? (
                            <button
                              type="button"
                              className="org-btn-view-pill"
                              style={{ color: '#047857' }}
                              onClick={() => handleLifecycleAction(grp.id, 'resume')}
                            >
                              Resume
                            </button>
                          ) : null}
                          {grp.status !== 'CLOSED' && (
                            <button
                              type="button"
                              className="org-btn-view-pill"
                              style={{ color: '#dc2626' }}
                              onClick={() => {
                                if (window.confirm(`Are you sure you want to close "${grp.name}" according to lifecycle rules?`)) {
                                  handleLifecycleAction(grp.id, 'close');
                                }
                              }}
                            >
                              Close
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 3: MEMBERS MODULE */}
          {activeTab === 'members' && (
            <div className="org-card">
              <div className="org-card-header">
                <div>
                  <h2 className="org-card-title">
                    {t('orgNavMembers') || 'Members Management'}
                  </h2>
                  <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                    Active members, pending membership requests, and invitation tokens.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <select
                    className="org-select"
                    value={selectedGroup?.id || ''}
                    onChange={(e) => {
                      const g = groups.find((item) => item.id === e.target.value);
                      if (g) handleGroupSelect(g);
                    }}
                  >
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>{g.name}</option>
                    ))}
                  </select>
                  {!groupMembers.some((m) => (m.email === user?.email || (user?.id && String(m.user_id) === String(user.id))) && (m.roles?.some(r => String(r).toLowerCase().includes('member')) || m.roles?.includes('GROUP_MEMBER'))) && (
                    <button
                      type="button"
                      className="org-btn-primary"
                      style={{ background: '#2563eb', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                      onClick={handleJoinSelectedGroupAsMember}
                      title="Enroll yourself as a participating member into the rotation payout schedule and contribution obligations"
                    >
                      <UserCheck size={16} /> Join as Member
                    </button>
                  )}
                  <button
                    type="button"
                    className="org-btn-primary"
                    style={{ background: '#10b981', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                    onClick={() => {
                      setAddMemberForm({
                        full_name: '',
                        email: '',
                        phone_number: '',
                        password_setup_method: 'TEMPORARY_PASSWORD',
                        initial_password: 'EqubMember@123'
                      });
                      setAddMemberResult(null);
                      setShowAddMemberModal(true);
                    }}
                  >
                    <Plus size={15} /> Add Member
                  </button>
                  <button
                    type="button"
                    className="org-btn-secondary"
                    onClick={() => setShowInviteModal(true)}
                  >
                    + Invite Link
                  </button>
                  <button
                    type="button"
                    className="org-btn-secondary"
                    onClick={() => setShowAssignTreasurerModal(true)}
                  >
                    Assign Treasurer
                  </button>
                </div>
              </div>

              {/* Pending Requests Section */}
              {membershipRequests.length > 0 && (
                <div style={{ marginBottom: '1.5rem', padding: '1rem', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '8px' }}>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#92400e', marginBottom: '0.5rem' }}>
                    Pending Membership Requests ({membershipRequests.length})
                  </h3>
                  <table className="org-table">
                    <thead>
                      <tr>
                        <th>Applicant Name</th>
                        <th>Email</th>
                        <th>Phone</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {membershipRequests.map((req) => (
                        <tr key={req.membership_id}>
                          <td style={{ fontWeight: 700 }}>{req.full_name}</td>
                          <td>{req.email}</td>
                          <td>{req.phone_number || 'N/A'}</td>
                          <td>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                              <button
                                type="button"
                                className="org-btn-primary"
                                style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', background: '#10b981' }}
                                onClick={() => handleMembershipRequestAction(req.membership_id, 'approve')}
                              >
                                Approve
                              </button>
                              <button
                                type="button"
                                className="org-btn-secondary"
                                style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', color: '#b91c1c' }}
                                onClick={() => handleMembershipRequestAction(req.membership_id, 'reject')}
                              >
                                Reject
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Active Members Table */}
              <table className="org-table">
                <thead>
                  <tr>
                    <th>Member</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>Role</th>
                    <th>Payout Order</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {groupMembers.map((m) => (
                    <tr key={m.membership_id}>
                      <td style={{ fontWeight: 700 }}>{m.full_name}</td>
                      <td>{m.email}</td>
                      <td>{m.phone_number || 'N/A'}</td>
                      <td>
                        <span className="org-badge org-badge-blue">
                          {m.roles?.join(', ') || 'Member'}
                        </span>
                      </td>
                      <td>#{m.payout_order_index || '—'}</td>
                      <td>
                        <span className={`org-badge ${m.status === 'ACTIVE' ? 'org-badge-green' : 'org-badge-orange'}`}>{m.status}</span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="org-btn-view-pill"
                          onClick={() => handleOpenMemberDetail(m.membership_id)}
                        >
                          Manage
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 4: CONTRIBUTIONS MODULE */}
          {activeTab === 'contributions' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* SECTION A: Organizer Personal Contribution Obligations */}
              <div className="org-card org-personal-obligations-card">
                <div className="org-card-header" style={{ flexWrap: 'wrap', gap: '1rem', alignItems: 'center' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <Wallet size={22} color="#2563eb" />
                      <h2 className="org-personal-obligations-title">
                        Personal Contribution Obligations
                      </h2>
                      <span className="org-badge org-badge-blue">
                        You (Organizer Member)
                      </span>
                    </div>
                    <p className="org-personal-obligations-subtitle" style={{ fontSize: '0.82rem', marginTop: '0.25rem' }}>
                      Your individual savings obligations as a participating member across your Equb groups.
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
                    {/* Group Selector Dropdown */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <label style={{ fontSize: '0.8rem', fontWeight: 600 }}>Group:</label>
                      <select
                        className="org-select"
                        value={personalSelectedGroupId}
                        onChange={(e) => setPersonalSelectedGroupId(e.target.value)}
                        style={{ maxWidth: '220px', padding: '0.4rem 0.6rem', fontSize: '0.82rem' }}
                      >
                        <option value="ALL">All My Groups ({personalObligations.length})</option>
                        {groups.map((g) => (
                          <option key={g.id} value={g.id}>{g.name}</option>
                        ))}
                      </select>
                    </div>

                    {/* Status Filter Pills */}
                    <div style={{ display: 'flex', gap: '0.35rem' }}>
                      {['ALL', 'PENDING', 'PAID', 'OVERDUE'].map((st) => (
                        <button
                          key={st}
                          type="button"
                          onClick={() => setPersonalContributionFilter(st)}
                          className={`org-filter-pill ${personalContributionFilter === st ? 'active' : ''}`}
                        >
                          {st}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Personal Obligations Table */}
                <div className="org-table-responsive" style={{ margin: '0.5rem 0' }}>
                  <table className="org-table" style={{ margin: 0 }}>
                    <thead>
                      <tr>
                        <th>Group</th>
                        <th>Period</th>
                        <th>Due Date</th>
                        <th>Expected</th>
                        <th>Paid</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {personalObligations
                        .filter((ob) => {
                          const matchesGroup = personalSelectedGroupId === 'ALL' || ob.group_id === personalSelectedGroupId;
                          const matchesStatus = personalContributionFilter === 'ALL' || ob.status === personalContributionFilter;
                          return matchesGroup && matchesStatus;
                        })
                        .map((ob) => (
                          <tr key={ob.id}>
                            <td style={{ fontWeight: 700 }}>{ob.group_name}</td>
                            <td>Round #{ob.period_number || ob.period_round || 1}</td>
                            <td>{ob.due_date || '-'}</td>
                            <td style={{ fontWeight: 700 }}>ETB {Number(ob.expected_amount || 0).toLocaleString()}</td>
                            <td style={{ color: '#10b981', fontWeight: 700 }}>ETB {Number(ob.amount_paid || 0).toLocaleString()}</td>
                            <td>
                              <span className={`org-badge ${ob.status === 'PAID' ? 'org-badge-green' : ob.status === 'OVERDUE' ? 'org-badge-red' : 'org-badge-orange'}`}>
                                {ob.status_display || ob.status}
                              </span>
                            </td>
                            <td>
                              {ob.status !== 'PAID' ? (
                                <button
                                  type="button"
                                  className="org-btn-primary"
                                  onClick={() => handleInitiatePersonalPayment(ob)}
                                  style={{ padding: '0.35rem 0.8rem', fontSize: '0.8rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}
                                >
                                  <Wallet size={14} />
                                  <span>Pay Now</span>
                                </button>
                              ) : (
                                <span style={{ color: '#10b981', fontWeight: 700, fontSize: '0.82rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                                  <CheckCircle2 size={14} /> Paid
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      {personalObligations.filter((ob) => {
                        const matchesGroup = personalSelectedGroupId === 'ALL' || ob.group_id === personalSelectedGroupId;
                        const matchesStatus = personalContributionFilter === 'ALL' || ob.status === personalContributionFilter;
                        return matchesGroup && matchesStatus;
                      }).length === 0 && (
                        <tr>
                          <td colSpan="7" style={{ textAlign: 'center', padding: '1.5rem', color: '#94a3b8', fontStyle: 'italic' }}>
                            No personal contribution obligations found matching this filter.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* SECTION B: Group Obligations Monitoring */}
              <div className="org-card">
                <div className="org-card-header">
                  <div>
                    <h2 className="org-card-title">
                      {t('orgNavContributions') || 'Group Contributions Monitoring'}
                    </h2>
                    <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                      Track confirmed collections, overdue member obligations, and payment methods for {selectedGroup?.name || 'selected group'}.
                    </p>
                  </div>
                  <select
                    className="org-select"
                    value={selectedGroup?.id || ''}
                    onChange={(e) => {
                      const g = groups.find((item) => item.id === e.target.value);
                      if (g) handleGroupSelect(g);
                    }}
                    style={{ maxWidth: '250px' }}
                  >
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>{g.name}</option>
                    ))}
                  </select>
                </div>

                {groupContributions && (
                  <div className="org-kpi-grid" style={{ marginBottom: '1.25rem' }}>
                    <div className="org-kpi-card">
                      <div className="org-kpi-content">
                        <div className="org-kpi-value">ETB {Number(groupContributions.summary?.total_expected_etb || 0).toLocaleString()}</div>
                        <div className="org-kpi-label">Total Expected</div>
                      </div>
                    </div>
                    <div className="org-kpi-card">
                      <div className="org-kpi-content">
                        <div className="org-kpi-value" style={{ color: '#10b981' }}>
                          ETB {Number(groupContributions.summary?.total_collected_etb || 0).toLocaleString()}
                        </div>
                        <div className="org-kpi-label">Total Confirmed</div>
                      </div>
                    </div>
                    <div className="org-kpi-card">
                      <div className="org-kpi-content">
                        <div className="org-kpi-value">{groupContributions.summary?.collection_rate_pct || 0}%</div>
                        <div className="org-kpi-label">Collection Rate</div>
                      </div>
                    </div>
                    <div className="org-kpi-card">
                      <div className="org-kpi-content">
                        <div className="org-kpi-value" style={{ color: '#ef4444' }}>
                          {groupContributions.summary?.overdue_count || 0}
                        </div>
                        <div className="org-kpi-label">Overdue Obligations</div>
                      </div>
                    </div>
                  </div>
                )}

                <table className="org-table">
                  <thead>
                    <tr>
                      <th>Member</th>
                      <th>Due Date</th>
                      <th>Expected (ETB)</th>
                      <th>Amount Paid</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(groupContributions?.obligations || []).map((ob) => {
                      const isCurrentUser = ob.is_me || ob.member_email === user?.email || (user?.id && String(ob.member_user_id) === String(user.id));
                      return (
                        <tr key={ob.id} className={isCurrentUser ? 'org-current-user-row' : ''}>
                          <td style={{ fontWeight: 700 }}>
                            {ob.member_name}
                            {isCurrentUser && (
                              <span style={{ fontSize: '0.7rem', background: '#2563eb', color: '#fff', padding: '0.1rem 0.4rem', borderRadius: '4px', marginLeft: '0.5rem' }}>
                                You (Organizer)
                              </span>
                            )}
                          </td>
                          <td>{ob.due_date}</td>
                          <td>ETB {Number(ob.expected_amount).toLocaleString()}</td>
                          <td style={{ fontWeight: 600 }}>ETB {Number(ob.amount_paid).toLocaleString()}</td>
                          <td>
                            <span className={`org-badge ${ob.status === 'PAID' ? 'org-badge-green' : ob.status === 'OVERDUE' ? 'org-badge-red' : 'org-badge-orange'}`}>
                              {ob.status}
                            </span>
                          </td>
                          <td>
                            {isCurrentUser && ob.status !== 'PAID' ? (
                              <button
                                type="button"
                                className="org-btn-primary"
                                style={{ padding: '0.25rem 0.65rem', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                                onClick={() => {
                                  const match = personalObligations.find((p) => p.id === ob.id) || {
                                    ...ob,
                                    group_name: selectedGroup?.name,
                                    period_number: ob.period_round || 1,
                                    remaining_amount: (Number(ob.expected_amount) - Number(ob.amount_paid)).toFixed(2)
                                  };
                                  handleInitiatePersonalPayment(match);
                                }}
                              >
                                <Wallet size={12} />
                                <span>Pay Now</span>
                              </button>
                            ) : (
                              <span style={{ color: '#94a3b8', fontSize: '0.8rem' }}>—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 5: PAYOUTS MODULE */}
          {activeTab === 'payouts' && (
            <div className="org-card">
              <div className="org-card-header">
                <div>
                  <h2 className="org-card-title">
                    {t('orgNavPayouts') || 'Payout Management'}
                  </h2>
                  <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                    Track verified collections, rotating round disbursements, recipient schedules, and dual authorization.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                  <select
                    className="org-select"
                    value={selectedGroup?.id || ''}
                    onChange={(e) => {
                      const g = groups.find((item) => item.id === e.target.value);
                      if (g) handleGroupSelect(g);
                    }}
                  >
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>{g.name}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="org-btn-primary"
                    onClick={() => setShowSchedulePayoutModal(true)}
                  >
                    + Schedule Payout
                  </button>
                </div>
              </div>

              {/* Pool & Collection Formula Breakdown */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: '0.85rem',
                margin: '1rem 0 1.25rem',
                padding: '1rem',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
              }}>
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Active Group Members</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a' }}>
                    {groupPayoutsData?.active_members_count || groupMembers.length}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Expected Collection (Total Pool)</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#2563eb' }}>
                    ETB {Number(groupPayoutsData?.expected_collection_etb || (selectedGroup ? Number(selectedGroup.contribution_amount) * (groupMembers.length || 1) : 0)).toLocaleString()}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Verified Treasury Funds</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#059669' }}>
                    ETB {Number(groupPayoutsData?.actual_verified_collection_etb || groupPayoutsData?.available_funds_etb || 0).toLocaleString()}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Platform Fee (0%)</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#64748b' }}>
                    ETB 0.00
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Payout per Winner</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#d97706' }}>
                    ETB {Number(groupPayoutsData?.payout_amount_etb || (selectedGroup ? Number(selectedGroup.contribution_amount) * (groupMembers.length || 1) : 0)).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Status Filter Pills */}
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                {['ALL', 'PENDING_APPROVAL', 'APPROVED', 'COMPLETED', 'BLOCKED_INSUFFICIENT_FUNDS'].map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setPayoutStatusFilter(st)}
                    style={{
                      padding: '0.3rem 0.75rem',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      borderRadius: '6px',
                      cursor: 'pointer',
                      border: '1px solid',
                      background: payoutStatusFilter === st ? '#2563eb' : '#ffffff',
                      color: payoutStatusFilter === st ? '#ffffff' : '#475569',
                      borderColor: payoutStatusFilter === st ? '#2563eb' : '#cbd5e1'
                    }}
                  >
                    {st.replace(/_/g, ' ')}
                  </button>
                ))}
              </div>

              <table className="org-table">
                <thead>
                  <tr>
                    <th>Recipient</th>
                    <th>Amount (ETB)</th>
                    <th>Status</th>
                    <th>Settlement Status</th>
                    <th>Transaction Ref / Payout ID</th>
                    <th>Requested At</th>
                  </tr>
                </thead>
                <tbody>
                  {(groupPayouts.filter(p => payoutStatusFilter === 'ALL' || p.status === payoutStatusFilter)).map((p) => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 700 }}>{p.recipient_name}</td>
                      <td style={{ fontWeight: 800 }}>ETB {Number(p.amount).toLocaleString()}</td>
                      <td>
                        <span className={`org-badge ${p.status === 'APPROVED' ? 'org-badge-green' : p.status === 'COMPLETED' ? 'org-badge-blue' : p.status === 'BLOCKED_INSUFFICIENT_FUNDS' ? 'org-badge-red' : 'org-badge-orange'}`}>
                          {p.status}
                        </span>
                      </td>
                      <td style={{ color: '#64748b' }}>{p.settlement_status || 'AWAITING_SETTLEMENT'}</td>
                      <td>
                        <code style={{ fontSize: '0.72rem', background: '#f1f5f9', padding: '0.2rem 0.4rem', borderRadius: '4px' }}>
                          {p.transaction_reference || p.id.slice(0, 8)}
                        </code>
                      </td>
                      <td>{new Date(p.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                  {groupPayouts.length === 0 && (
                    <tr>
                      <td colSpan="6" style={{ textAlign: 'center', padding: '1.5rem', color: '#64748b' }}>
                        No payouts scheduled or executed for this group yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB: DIGITAL EQUB LOTTERY & CYCLE MANAGEMENT */}
          {activeTab === 'lottery' && (
            <div>
              {/* Group Selector & Cycle Overview Card */}
              <div className="org-card" style={{ marginBottom: '1.25rem' }}>
                <div className="org-card-header" style={{ flexWrap: 'wrap', gap: '1rem' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <h2 className="org-card-title">{t('orgNavLottery') || 'Digital Equb Lottery & Cycle Manager'}</h2>
                      <span className="org-badge org-badge-blue">
                        Cycle #{lotteryData?.cycle?.cycle_number || selectedGroup?.current_cycle_number || 1}
                      </span>
                      {lotteryData?.group?.is_lottery_locked ? (
                        <span className="org-badge org-badge-gray" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                          <Lock size={12} /> Locked Method
                        </span>
                      ) : (
                        <span className="org-badge org-badge-green">Configurable</span>
                      )}
                    </div>
                    <p style={{ fontSize: '0.82rem', color: '#64748b', marginTop: '0.25rem' }}>
                      Autonomous cycle execution, cryptographic SHA-256 draw verification, and complete cycle completion auditing.
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <select
                      className="org-select"
                      style={{ width: 'auto', minWidth: '180px' }}
                      value={selectedGroup?.id || ''}
                      onChange={(e) => {
                        const g = groups.find((grp) => grp.id === e.target.value);
                        if (g) handleGroupSelect(g);
                      }}
                    >
                      {groups.map((g) => (
                        <option key={g.id} value={g.id}>
                          {g.name}
                        </option>
                      ))}
                    </select>

                    <button
                      type="button"
                      className="org-btn-secondary"
                      onClick={() => selectedGroup?.id && loadGroupSubData(selectedGroup.id)}
                      disabled={refreshing}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                    >
                      <RefreshCw size={14} className={refreshing ? 'org-spin' : ''} />
                      <span>Sync</span>
                    </button>

                    {lotteryData?.cycle?.status === 'COMPLETED' ? (
                      <button
                        type="button"
                        className="org-btn-primary"
                        onClick={handleStartNextCycle}
                        disabled={startingCycle}
                        style={{ background: '#059669', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
                      >
                        {startingCycle ? <RefreshCw size={14} className="org-spin" /> : <Sparkles size={14} />}
                        <span>Start Next Cycle #{Number(lotteryData?.cycle?.cycle_number || 1) + 1}</span>
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="org-btn-primary"
                        onClick={handleTriggerLotteryDraw}
                        disabled={drawingLottery}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
                      >
                        {drawingLottery ? <RefreshCw size={14} className="org-spin" /> : <Award size={14} />}
                        <span>Execute / Verify Draw</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Method & Status Information Bar */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid #e2e8f0' }}>
                  <div style={{ background: '#f8fafc', padding: '0.85rem', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                      Lottery Method (Dropdown 1)
                    </div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a', marginTop: '0.25rem' }}>
                      {lotteryData?.group?.lottery_method === 'METHOD_A'
                        ? 'Option A – One-time lottery'
                        : 'Option B – Round-by-round lottery'}
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '0.2rem' }}>
                      {lotteryData?.group?.lottery_method === 'METHOD_A'
                        ? 'Payout order generated once at cycle start and strictly preserved across rounds.'
                        : 'Randomized draw conducted each round from remaining eligible active members.'}
                    </div>
                  </div>

                  <div style={{ background: '#f8fafc', padding: '0.85rem', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                      Current Round & Stage
                    </div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a', marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span>Round #{lotteryData?.current_round?.round_number || 1}</span>
                      <span className={`org-badge ${lotteryData?.current_round?.is_postponed ? 'org-badge-red' : (lotteryData?.current_round?.status === 'DRAWN' ? 'org-badge-green' : 'org-badge-blue')}`}>
                        {lotteryData?.current_round?.status || 'SCHEDULED'}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '0.2rem' }}>
                      Scheduled: {lotteryData?.current_round?.scheduled_date || 'Pending Cycle Start'} • Grace: {lotteryData?.group?.grace_period_days || 3} days
                    </div>
                  </div>

                  <div style={{ background: '#f8fafc', padding: '0.85rem', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
                      Cycle Progress
                    </div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 800, color: '#0f172a', marginTop: '0.25rem' }}>
                      {(lotteryData?.winners_history || []).length} / {groupMembers.length} Members Won
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '0.2rem' }}>
                      Pool: ETB {Number((selectedGroup?.contribution_amount || 0) * groupMembers.length).toLocaleString()} per round
                    </div>
                  </div>
                </div>

                {/* POSTPONED ALERT BANNER */}
                {(lotteryData?.current_round?.is_postponed || (!lotteryData?.readiness?.is_ready && lotteryData?.readiness?.pending_unpaid_count > 0)) && (
                  <div style={{ marginTop: '1.25rem', padding: '1rem', background: '#fffbeb', borderRadius: '10px', border: '1px solid #fde68a', color: '#92400e' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 800, fontSize: '0.92rem' }}>
                      <AlertTriangle size={18} color="#d97706" />
                      <span>Round #{lotteryData?.current_round?.round_number || 1} Lottery Draw Postponed</span>
                    </div>
                    <div style={{ fontSize: '0.82rem', marginTop: '0.35rem', lineHeight: 1.5 }}>
                      <strong>Reason:</strong> {lotteryData?.current_round?.postponed_reason || (lotteryData?.readiness?.reasons || []).join('; ') || 'Active member contribution obligations remain unpaid.'}
                    </div>
                    <div style={{ fontSize: '0.78rem', marginTop: '0.4rem', color: '#b45309' }}>
                      🛡️ <strong>Digital Equb Integrity Policy:</strong> Under system rules, the lottery is automatically paused if any active member contributions are incomplete. To resolve this, use the <strong>Overdue Resolution</strong> tab to apply Option A (Continue Waiting), Option B (Payment Agreement), or Option C (Membership Review).
                    </div>
                  </div>
                )}
              </div>

              {/* METHOD A: PREDETERMINED PAYOUT ORDER SEQUENCE TABLE */}
              {lotteryData?.group?.lottery_method === 'METHOD_A' && (
                <div className="org-card" style={{ marginBottom: '1.5rem' }}>
                  <div className="org-card-header">
                    <div>
                      <h3 className="org-card-title">Full Cycle Payout Sequence (Option A – One-time Draw)</h3>
                      <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                        The complete randomized rotation order was locked at cycle initialization and is strictly followed round-by-round.
                      </p>
                    </div>
                  </div>

                  <table className="org-table">
                    <thead>
                      <tr>
                        <th style={{ width: '80px' }}>Draw Order</th>
                        <th>Member Name</th>
                        <th>Contact Email</th>
                        <th>Expected Payout Round</th>
                        <th>Status</th>
                        <th>Disbursement</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(lotteryData?.predetermined_order || []).map((item, idx) => {
                        const winnerRecord = (lotteryData?.winners_history || []).find(w => String(w.winner_membership) === String(item.membership_id));
                        const isCurrent = Number(item.round_number) === Number(lotteryData?.current_round?.round_number);
                        return (
                          <tr key={idx} style={{ background: isCurrent ? 'rgba(37, 99, 235, 0.04)' : undefined }}>
                            <td style={{ fontWeight: 800 }}>
                              <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', borderRadius: '50%', background: winnerRecord ? '#ecfdf5' : '#eff6ff', color: winnerRecord ? '#059669' : '#2563eb' }}>
                                #{item.draw_position || idx + 1}
                              </span>
                            </td>
                            <td style={{ fontWeight: 700 }}>{item.member_name}</td>
                            <td style={{ color: '#64748b' }}>{item.member_email}</td>
                            <td>Round #{item.round_number}</td>
                            <td>
                              {winnerRecord ? (
                                <span className="org-badge org-badge-green" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}>
                                  <CheckCircle2 size={12} /> Won (Round #{winnerRecord.round_number})
                                </span>
                              ) : isCurrent ? (
                                <span className="org-badge org-badge-blue">Current Round Target</span>
                              ) : (
                                <span className="org-badge org-badge-gray">Upcoming</span>
                              )}
                            </td>
                            <td style={{ fontWeight: 700 }}>
                              ETB {Number(selectedGroup?.contribution_amount || 0) * groupMembers.length ? (Number(selectedGroup.contribution_amount) * groupMembers.length).toLocaleString() : '—'}
                            </td>
                          </tr>
                        );
                      })}
                      {(!lotteryData?.predetermined_order || lotteryData.predetermined_order.length === 0) && (
                        <tr>
                          <td colSpan="6" style={{ textAlign: 'center', padding: '1.5rem', color: '#64748b' }}>
                            Predetermined order will be drawn and locked on the first round execution.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {/* METHOD B: REMAINING CANDIDATES POOL */}
              {lotteryData?.group?.lottery_method === 'METHOD_B' && (
                <div className="org-card" style={{ marginBottom: '1.5rem' }}>
                  <div className="org-card-header">
                    <div>
                      <h3 className="org-card-title">Round-by-Round Candidate Pool (Option B)</h3>
                      <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                        Eligible members participating in future draws for this cycle who have not yet won.
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.85rem' }}>
                    {(lotteryData?.candidates || []).map((cand) => (
                      <div
                        key={cand.id}
                        style={{
                          padding: '1rem',
                          borderRadius: '10px',
                          border: cand.has_won ? '1px solid #e2e8f0' : '1px solid #bfdbfe',
                          background: cand.has_won ? '#f8fafc' : '#eff6ff',
                          opacity: cand.has_won ? 0.6 : 1
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ fontWeight: 700, fontSize: '0.92rem', color: '#0f172a' }}>{cand.name}</div>
                          {cand.has_won ? (
                            <span className="org-badge org-badge-green">Won</span>
                          ) : (
                            <span className="org-badge org-badge-blue">Eligible</span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '0.25rem' }}>{cand.email}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* PREVIOUS WINNERS & VERIFIABLE SHA-256 AUDIT HASH TABLE */}
              <div className="org-card">
                <div className="org-card-header">
                  <div>
                    <h3 className="org-card-title">Draw Winners & Verifiable Audit Log</h3>
                    <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                      Every lottery draw is cryptographically secured with Python's secrets.SystemRandom() and audited with verifiable SHA-256 hashes.
                    </p>
                  </div>
                </div>

                <table className="org-table">
                  <thead>
                    <tr>
                      <th>Round #</th>
                      <th>Winner Member</th>
                      <th>Disbursed Payout</th>
                      <th>Draw Timestamp</th>
                      <th>Verifiable SHA-256 Hash</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(lotteryData?.winners_history || []).map((w) => (
                      <tr key={w.id}>
                        <td style={{ fontWeight: 800 }}>Round #{w.round_number}</td>
                        <td style={{ fontWeight: 700 }}>
                          <div>{w.winner_name}</div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{w.winner_email}</div>
                        </td>
                        <td style={{ fontWeight: 800, color: '#16a34a' }}>
                          ETB {Number(w.payout_amount || 0).toLocaleString()}
                        </td>
                        <td>{new Date(w.drawn_at).toLocaleString()}</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <code
                              style={{
                                fontSize: '0.72rem',
                                background: '#f1f5f9',
                                padding: '0.25rem 0.5rem',
                                borderRadius: '4px',
                                fontFamily: 'monospace',
                                color: '#0f172a'
                              }}
                              title={w.sha256_hash}
                            >
                              {w.sha256_hash ? `${w.sha256_hash.slice(0, 16)}...` : 'N/A'}
                            </code>
                            {w.sha256_hash && (
                              <button
                                type="button"
                                onClick={() => {
                                  navigator.clipboard.writeText(w.sha256_hash);
                                  setSuccessMsg('Verification SHA-256 Hash copied to clipboard!');
                                  setTimeout(() => setSuccessMsg(''), 3000);
                                }}
                                style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#64748b', padding: '0.2rem' }}
                                title="Copy Full Hash"
                              >
                                <Copy size={13} />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {(!lotteryData?.winners_history || lotteryData.winners_history.length === 0) && (
                      <tr>
                        <td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                          No winners drawn for this cycle yet. Execute the first lottery draw once active contributions are completed.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB: OVERDUE CONTRIBUTION RESOLUTION SYSTEM (Dropdown 2: A, B, C) */}
          {activeTab === 'overdue' && (
            <div>
              {/* Header & Evaluation Trigger */}
              <div className="org-card" style={{ marginBottom: '1.25rem' }}>
                <div className="org-card-header" style={{ flexWrap: 'wrap', gap: '1rem' }}>
                  <div>
                    <h2 className="org-card-title">{t('orgNavOverdue') || 'Overdue Contribution Resolution System'}</h2>
                    <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                      Automated due date tracking, daily reminder enforcement, grace period management, and authorized group resolutions (Dropdown 2).
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <select
                      className="org-select"
                      style={{ width: 'auto', minWidth: '180px' }}
                      value={selectedGroup?.id || ''}
                      onChange={(e) => {
                        const g = groups.find((grp) => grp.id === e.target.value);
                        if (g) handleGroupSelect(g);
                      }}
                    >
                      {groups.map((g) => (
                        <option key={g.id} value={g.id}>
                          {g.name}
                        </option>
                      ))}
                    </select>

                    <button
                      type="button"
                      className="org-btn-primary"
                      onClick={handleEvaluateOverdue}
                      disabled={evaluatingOverdue}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
                    >
                      {evaluatingOverdue ? <RefreshCw size={14} className="org-spin" /> : <Clock size={14} />}
                      <span>Evaluate Deadlines & Grace Periods</span>
                    </button>
                  </div>
                </div>

                {/* Overdue Categories Dropdown Form Filter */}
                <div className="org-overdue-filter-section" style={{ marginTop: '1.25rem', paddingTop: '1.25rem', borderTop: '1px solid var(--org-border, #e2e8f0)' }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', marginBottom: '1.25rem', background: 'var(--org-bg-muted, rgba(37, 99, 235, 0.04))', padding: '1rem 1.25rem', borderRadius: '12px', border: '1px solid var(--org-border, #e2e8f0)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                      <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'rgba(37, 99, 235, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#2563eb' }}>
                        <Filter size={18} />
                      </div>
                      <div>
                        <label htmlFor="overdue-category-select-form" style={{ fontWeight: 800, fontSize: '0.95rem', color: 'var(--org-text-main, #0f172a)', display: 'block' }}>
                          Overdue Categories Dropdown Form
                        </label>
                        <span style={{ fontSize: '0.78rem', color: 'var(--org-text-muted, #64748b)' }}>
                          Select a category from the dropdown to filter the overdue register table below:
                        </span>
                      </div>
                    </div>

                    {/* Dropdown Form */}
                    <div style={{ minWidth: '320px', flex: '1 1 320px', maxWidth: '460px' }}>
                      <select
                        id="overdue-category-select-form"
                        className="org-select"
                        value={overdueCategoryFilter}
                        onChange={(e) => setOverdueCategoryFilter(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '0.65rem 1rem',
                          fontSize: '0.9rem',
                          fontWeight: 700,
                          borderRadius: '10px',
                          cursor: 'pointer',
                          background: 'var(--org-card-bg, #ffffff)',
                          color: 'var(--org-text-main, #0f172a)',
                          borderColor: 'var(--org-border, #cbd5e1)'
                        }}
                      >
                        <option value="ALL">1. Total Overdue Cases ({(overdueCases || []).length})</option>
                        <option value="PENDING">2. Pending Resolution ({(overdueCases || []).filter(c => c.status === 'PENDING').length})</option>
                        <option value="RESOLVED_WAITING">3. Waiting Extensions (A) ({(overdueCases || []).filter(c => c.status === 'RESOLVED_WAITING').length})</option>
                        <option value="RESOLVED_AGREEMENT">4. Payment Agreements (B) ({(overdueCases || []).filter(c => c.status === 'RESOLVED_AGREEMENT').length})</option>
                      </select>
                    </div>
                  </div>

                  {/* Overdue Overview KPIs (Cards synced with the dropdown, fully theme-adaptive) */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                    <div
                      onClick={() => setOverdueCategoryFilter('ALL')}
                      className={`org-overdue-kpi-card ${overdueCategoryFilter === 'ALL' ? 'active-kpi' : ''}`}
                      style={{
                        padding: '1rem',
                        borderRadius: '10px',
                        border: overdueCategoryFilter === 'ALL' ? '2px solid #2563eb' : '1px solid var(--org-border, #e2e8f0)',
                        background: 'var(--org-card-bg, #ffffff)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--org-text-muted, #64748b)', textTransform: 'uppercase' }}>Total Overdue Cases</div>
                      <div style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--org-text-main, #0f172a)', marginTop: '0.2rem' }}>
                        {(overdueCases || []).length}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#2563eb', marginTop: '0.35rem', fontWeight: 600 }}>
                        {overdueCategoryFilter === 'ALL' ? '● Currently viewing in table' : 'Click to select in dropdown'}
                      </div>
                    </div>

                    <div
                      onClick={() => setOverdueCategoryFilter('PENDING')}
                      className={`org-overdue-kpi-card ${overdueCategoryFilter === 'PENDING' ? 'active-kpi' : ''}`}
                      style={{
                        padding: '1rem',
                        borderRadius: '10px',
                        border: overdueCategoryFilter === 'PENDING' ? '2px solid #dc2626' : '1px solid var(--org-border, #e2e8f0)',
                        background: 'var(--org-card-bg, #ffffff)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--org-text-muted, #64748b)', textTransform: 'uppercase' }}>Pending Resolution</div>
                      <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#dc2626', marginTop: '0.2rem' }}>
                        {(overdueCases || []).filter(c => c.status === 'PENDING').length}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#dc2626', marginTop: '0.35rem', fontWeight: 600 }}>
                        {overdueCategoryFilter === 'PENDING' ? '● Currently viewing in table' : 'Click to select in dropdown'}
                      </div>
                    </div>

                    <div
                      onClick={() => setOverdueCategoryFilter('RESOLVED_WAITING')}
                      className={`org-overdue-kpi-card ${overdueCategoryFilter === 'RESOLVED_WAITING' ? 'active-kpi' : ''}`}
                      style={{
                        padding: '1rem',
                        borderRadius: '10px',
                        border: overdueCategoryFilter === 'RESOLVED_WAITING' ? '2px solid #d97706' : '1px solid var(--org-border, #e2e8f0)',
                        background: 'var(--org-card-bg, #ffffff)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--org-text-muted, #64748b)', textTransform: 'uppercase' }}>Waiting Extensions (A)</div>
                      <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#d97706', marginTop: '0.2rem' }}>
                        {(overdueCases || []).filter(c => c.status === 'RESOLVED_WAITING').length}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#d97706', marginTop: '0.35rem', fontWeight: 600 }}>
                        {overdueCategoryFilter === 'RESOLVED_WAITING' ? '● Currently viewing in table' : 'Click to select in dropdown'}
                      </div>
                    </div>

                    <div
                      onClick={() => setOverdueCategoryFilter('RESOLVED_AGREEMENT')}
                      className={`org-overdue-kpi-card ${overdueCategoryFilter === 'RESOLVED_AGREEMENT' ? 'active-kpi' : ''}`}
                      style={{
                        padding: '1rem',
                        borderRadius: '10px',
                        border: overdueCategoryFilter === 'RESOLVED_AGREEMENT' ? '2px solid #2563eb' : '1px solid var(--org-border, #e2e8f0)',
                        background: 'var(--org-card-bg, #ffffff)',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--org-text-muted, #64748b)', textTransform: 'uppercase' }}>Payment Agreements (B)</div>
                      <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#2563eb', marginTop: '0.2rem' }}>
                        {(overdueCases || []).filter(c => c.status === 'RESOLVED_AGREEMENT').length}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: '#2563eb', marginTop: '0.35rem', fontWeight: 600 }}>
                        {overdueCategoryFilter === 'RESOLVED_AGREEMENT' ? '● Currently viewing in table' : 'Click to select in dropdown'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Overdue Cases Table */}
              <div className="org-card">
                <div className="org-card-header">
                  <div>
                    <h3 className="org-card-title">Group Overdue Cases Register</h3>
                    <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                      When a member misses payment past the {selectedGroup?.grace_period_days || 3}-day grace period, select an authorized resolution from Dropdown 2.
                    </p>
                  </div>
                </div>

                <table className="org-table">
                  <thead>
                    <tr>
                      <th>Member</th>
                      <th>Overdue Amount</th>
                      <th>Original Deadline</th>
                      <th>Grace Status</th>
                      <th>Resolution Status</th>
                      <th>Resolution Details</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(overdueCases || [])
                      .filter((c) => {
                        if (overdueCategoryFilter === 'ALL') return true;
                        return c.status === overdueCategoryFilter;
                      })
                      .map((c) => (
                      <tr key={c.id}>
                        <td style={{ fontWeight: 700 }}>
                          <div>{c.member_name}</div>
                          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{c.member_email}</div>
                        </td>
                        <td style={{ fontWeight: 800, color: '#dc2626' }}>
                          ETB {Number(c.amount_overdue || 0).toLocaleString()}
                        </td>
                        <td>
                          <div>{c.original_deadline}</div>
                          <div style={{ fontSize: '0.72rem', color: '#64748b' }}>{c.days_overdue || 0} days overdue</div>
                        </td>
                        <td>
                          {c.grace_period_expired ? (
                            <span className="org-badge org-badge-red">Grace Expired</span>
                          ) : (
                            <span className="org-badge org-badge-orange">Within Grace Period</span>
                          )}
                        </td>
                        <td>
                          <span className={`org-badge ${c.status === 'PENDING' ? 'org-badge-red' : (c.status === 'RESOLVED_WAITING' ? 'org-badge-orange' : (c.status === 'RESOLVED_AGREEMENT' ? 'org-badge-blue' : 'org-badge-purple'))}`}>
                            {c.status}
                          </span>
                        </td>
                        <td style={{ fontSize: '0.8rem', maxWidth: '200px' }}>
                          {c.status === 'RESOLVED_WAITING' && (
                            <div style={{ color: '#92400e' }}>Waiting until {c.follow_up_date}</div>
                          )}
                          {c.status === 'RESOLVED_AGREEMENT' && (
                            <div style={{ color: '#1d4ed8' }}>
                              Agreement: {c.payment_agreement?.status || 'Active'} • {c.payment_agreement?.installments?.length || 0} installments
                            </div>
                          )}
                          {c.status === 'RESOLVED_REVIEW' && (
                            <div style={{ color: '#7c3aed' }}>
                              Review: {c.membership_review?.decision || 'Decided'}
                            </div>
                          )}
                          {c.resolution_reason && (
                            <div style={{ color: '#64748b', fontSize: '0.74rem', marginTop: '0.15rem' }}>
                              "{c.resolution_reason}"
                            </div>
                          )}
                          {!c.resolution_reason && c.status === 'PENDING' && (
                            <span style={{ color: '#94a3b8' }}>Awaiting resolution</span>
                          )}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="org-btn-primary"
                            onClick={() => handleOpenResolveModal(c)}
                            style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem' }}
                          >
                            Resolve (Dropdown 2)
                          </button>
                        </td>
                      </tr>
                    ))}
                    {(overdueCases || []).filter((c) => {
                      if (overdueCategoryFilter === 'ALL') return true;
                      return c.status === overdueCategoryFilter;
                    }).length === 0 && (
                      <tr>
                        <td colSpan="7" style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                          {(overdueCases || []).length === 0
                            ? `No overdue cases recorded for ${selectedGroup?.name}. All member contributions are up to date!`
                            : `No overdue cases found matching selected category. Select another option from the dropdown form above.`}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 6: SUBSCRIPTIONS MODULE */}
          {activeTab === 'subscriptions' && (
            <div>
              <div className="org-card" style={{ marginBottom: '1.5rem' }}>
                <div className="org-card-header">
                  <div>
                    <h2 className="org-card-title">
                      {t('orgNavSubscriptions') || 'SaaS Subscription & Billing'}
                    </h2>
                    <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                      Organizer platform access tier and group quotas. (Equb member funds remain strictly separated).
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    <span className="org-badge org-badge-green">
                      {subscriptionData?.subscription?.status || 'ACTIVE'}
                    </span>
                    <button
                      type="button"
                      className="org-btn-primary"
                      style={{ background: '#059669', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                      onClick={handleRenewSubscription}
                    >
                      <RefreshCw size={15} /> Pay / Renew via Chapa
                    </button>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Current Plan</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a' }}>
                      {subscriptionData?.subscription?.plan?.name || 'Growth Plan'}
                    </div>
                  </div>
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Plan Price</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#2563eb' }}>
                      ETB {Number(subscriptionData?.subscription?.plan?.price_etb || 600).toLocaleString()} <span style={{ fontSize: '0.75rem', color: '#64748b' }}>/ mo</span>
                    </div>
                  </div>
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Active Groups Usage</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a' }}>
                      {subscriptionData?.groups_used ?? groups.length} / {subscriptionData?.groups_allowed || 5}
                    </div>
                  </div>
                  <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Subscription Expiration / Renewal</div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#047857' }}>
                      {subscriptionData?.subscription?.expires_at ? new Date(subscriptionData.subscription.expires_at).toLocaleDateString() : 'Nov 30, 2026'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Available Plans Comparison */}
              <h3 style={{ fontSize: '1rem', fontWeight: 800, marginBottom: '0.75rem', color: '#0f172a' }}>
                Available SaaS Plans & Quota Upgrade
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
                {(subscriptionData?.available_plans || [
                  { id: '1', name: 'Starter Plan', max_active_groups: 1, price_etb: '0.00' },
                  { id: '2', name: 'Growth Plan', max_active_groups: 5, price_etb: '600.00' },
                  { id: '3', name: 'Enterprise Plan', max_active_groups: 50, price_etb: '2500.00' },
                ]).map((pl) => {
                  const currentPlanId = subscriptionData?.subscription?.plan?.id;
                  const currentPlanName = subscriptionData?.subscription?.plan?.name?.trim().toLowerCase();
                  const isCurrent = (currentPlanId && currentPlanId === pl.id) ||
                    (currentPlanName && currentPlanName === pl.name?.trim().toLowerCase());
                  return (
                    <div key={pl.id} className="org-card" style={{ border: isCurrent ? '2px solid #2563eb' : '1px solid #e2e8f0' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 style={{ fontSize: '1.1rem', fontWeight: 800 }}>{pl.name}</h3>
                        {isCurrent && <span className="org-badge org-badge-blue">Current</span>}
                      </div>
                      <div style={{ fontSize: '1.5rem', fontWeight: 800, margin: '0.75rem 0' }}>
                        ETB {Number(pl.price_etb).toLocaleString()} <span style={{ fontSize: '0.8rem', color: '#64748b' }}>/ month</span>
                      </div>
                      <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: '1rem' }}>
                        Allows up to <strong>{pl.max_active_groups} active Equb groups</strong>.
                      </p>
                      <button
                        type="button"
                        className="org-btn-primary"
                        onClick={() => handleUpgradePlan(pl.id)}
                        disabled={isCurrent}
                        style={{
                          opacity: isCurrent ? 0.6 : 1,
                          cursor: isCurrent ? 'default' : 'pointer',
                          background: isCurrent ? '#64748b' : (Number(pl.price_etb) === 0 ? '#059669' : '#2563eb'),
                          width: '100%',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '0.4rem',
                          fontWeight: 700
                        }}
                      >
                        {isCurrent
                          ? 'Active Plan'
                          : (Number(pl.price_etb) === 0
                              ? 'Activate Starter (Free)'
                              : `Pay with Chapa (ETB ${Number(pl.price_etb).toLocaleString()})`
                            )
                        }
                      </button>
                    </div>
                  );
                })}
              </div>

              {/* Invoices & Payment History */}
              <div className="org-card">
                <div className="org-card-header">
                  <div>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 800 }}>Subscription Invoices & Payment History</h3>
                    <p style={{ fontSize: '0.8rem', color: '#64748b' }}>Official SaaS platform billing receipts and VAT compliance.</p>
                  </div>
                </div>
                <table className="org-table">
                  <thead>
                    <tr>
                      <th>Invoice #</th>
                      <th>Amount (ETB)</th>
                      <th>Status</th>
                      <th>Due Date</th>
                      <th>Paid Date</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(subscriptionData?.invoices || []).map((inv) => (
                      <tr key={inv.id}>
                        <td style={{ fontWeight: 700 }}>
                          <code style={{ background: '#f1f5f9', padding: '0.2rem 0.4rem', borderRadius: '4px' }}>
                            {inv.invoice_number}
                          </code>
                        </td>
                        <td style={{ fontWeight: 800 }}>ETB {Number(inv.amount_etb).toLocaleString()}</td>
                        <td>
                          <span className={`org-badge ${inv.status === 'PAID' ? 'org-badge-green' : 'org-badge-orange'}`}>
                            {inv.status}
                          </span>
                        </td>
                        <td>{inv.due_date ? new Date(inv.due_date).toLocaleDateString() : 'N/A'}</td>
                        <td>{inv.paid_at ? new Date(inv.paid_at).toLocaleDateString() : '—'}</td>
                        <td>
                          {inv.status !== 'PAID' ? (
                            <button
                              type="button"
                              className="org-btn-primary"
                              style={{ padding: '0.25rem 0.6rem', fontSize: '0.72rem', background: '#059669' }}
                              onClick={() => handlePaySubscription(null, subscriptionData?.subscription?.plan?.id)}
                            >
                              Pay via Chapa
                            </button>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: '#16a34a', fontWeight: 600 }}>✓ Settled</span>
                          )}
                        </td>
                      </tr>
                    ))}
                    {(!subscriptionData?.invoices || subscriptionData.invoices.length === 0) && (
                      <tr>
                        <td colSpan="6" style={{ textAlign: 'center', padding: '1.5rem', color: '#64748b' }}>
                          No past billing invoices recorded.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 7: REPORTS MODULE */}
          {activeTab === 'reports' && (
            <div className="org-card">
              <div className="org-card-header">
                <div>
                  <h2 className="org-card-title">
                    {t('orgNavReports') || 'Group Performance & Audited Reports'}
                  </h2>
                  <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                    Real-time financial analytics, attendance metrics, and protected CSV exports.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '0.6rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  <select
                    className="org-select"
                    value={selectedGroup?.id || ''}
                    onChange={(e) => {
                      const g = groups.find((item) => item.id === e.target.value);
                      if (g) handleGroupSelect(g);
                    }}
                  >
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>{g.name}</option>
                    ))}
                  </select>
                  {selectedGroup && (
                    <a
                      href={api.getOrganizerGroupReportExportUrl(selectedGroup.id)}
                      className="org-btn-secondary"
                      style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', textDecoration: 'none' }}
                      download
                    >
                      <Download size={15} /> Export CSV
                    </a>
                  )}
                  <button
                    type="button"
                    className="org-btn-secondary"
                    onClick={() => window.print()}
                    style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                  >
                    <Printer size={15} /> Print / PDF
                  </button>
                </div>
              </div>

              {reportData && (
                <div className="org-kpi-grid" style={{ marginBottom: '1.25rem' }}>
                  <div className="org-kpi-card">
                    <div className="org-kpi-content">
                      <div className="org-kpi-value">{reportData.kpis?.collection_rate_pct || 0}%</div>
                      <div className="org-kpi-label">Collection Rate</div>
                    </div>
                  </div>
                  <div className="org-kpi-card">
                    <div className="org-kpi-content">
                      <div className="org-kpi-value">{reportData.kpis?.total_members || 0}</div>
                      <div className="org-kpi-label">Active Members</div>
                    </div>
                  </div>
                  <div className="org-kpi-card">
                    <div className="org-kpi-content">
                      <div className="org-kpi-value">ETB {Number(reportData.kpis?.outstanding_total_etb || 0).toLocaleString()}</div>
                      <div className="org-kpi-label">Outstanding Balance</div>
                    </div>
                  </div>
                  <div className="org-kpi-card">
                    <div className="org-kpi-content">
                      <div className="org-kpi-value">{reportData.kpis?.completed_payouts || 0}</div>
                      <div className="org-kpi-label">Completed Payouts</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Report Category Switcher Pills */}
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
                {[
                  { id: 'COMPLIANCE', label: 'Member Compliance' },
                  { id: 'OUTSTANDING', label: 'Outstanding Contributions' },
                  { id: 'PAYOUTS', label: 'Payout History' },
                  { id: 'TREASURER', label: 'Treasurer Activity' },
                  { id: 'MONTHLY', label: 'Monthly Financial Summary' }
                ].map((cat) => (
                  <button
                    key={cat.id}
                    type="button"
                    onClick={() => setSelectedReportType(cat.id)}
                    style={{
                      padding: '0.35rem 0.8rem',
                      fontSize: '0.78rem',
                      fontWeight: 700,
                      borderRadius: '6px',
                      cursor: 'pointer',
                      border: '1px solid',
                      background: selectedReportType === cat.id ? '#2563eb' : '#ffffff',
                      color: selectedReportType === cat.id ? '#ffffff' : '#475569',
                      borderColor: selectedReportType === cat.id ? '#2563eb' : '#cbd5e1'
                    }}
                  >
                    {cat.label}
                  </button>
                ))}
              </div>

              {/* Report View 1: Member Compliance */}
              {selectedReportType === 'COMPLIANCE' && (
                <div>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                    Member Compliance & Contribution Velocity
                  </h3>
                  <table className="org-table">
                    <thead>
                      <tr>
                        <th>Member Name</th>
                        <th>Expected (ETB)</th>
                        <th>Paid (ETB)</th>
                        <th>Compliance %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(reportData?.member_performance || []).map((m, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 700 }}>{m.member_name}</td>
                          <td>ETB {Number(m.expected_etb).toLocaleString()}</td>
                          <td style={{ fontWeight: 600 }}>ETB {Number(m.paid_etb).toLocaleString()}</td>
                          <td>
                            <span className={`org-badge ${m.compliance_pct >= 90 ? 'org-badge-green' : 'org-badge-orange'}`}>
                              {m.compliance_pct}%
                            </span>
                          </td>
                        </tr>
                      ))}
                      {(!reportData?.member_performance || reportData.member_performance.length === 0) && (
                        <tr><td colSpan="4" style={{ textAlign: 'center', padding: '1.5rem', color: '#64748b' }}>No member compliance data available.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Report View 2: Outstanding Contributions */}
              {selectedReportType === 'OUTSTANDING' && (
                <div>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem', color: '#b91c1c' }}>
                    Outstanding & Overdue Contributions
                  </h3>
                  <table className="org-table">
                    <thead>
                      <tr>
                        <th>Member Name</th>
                        <th>Phone</th>
                        <th>Expected Amount</th>
                        <th>Amount Paid</th>
                        <th>Due Date</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(reportData?.outstanding_contributions || []).map((o, idx) => (
                        <tr key={idx}>
                          <td style={{ fontWeight: 700 }}>{o.member_name}</td>
                          <td>{o.phone || 'N/A'}</td>
                          <td style={{ fontWeight: 600 }}>ETB {Number(o.expected_etb).toLocaleString()}</td>
                          <td>ETB {Number(o.paid_etb).toLocaleString()}</td>
                          <td>{o.due_date ? new Date(o.due_date).toLocaleDateString() : 'N/A'}</td>
                          <td><span className="org-badge org-badge-orange">{o.status}</span></td>
                        </tr>
                      ))}
                      {(!reportData?.outstanding_contributions || reportData.outstanding_contributions.length === 0) && (
                        <tr><td colSpan="6" style={{ textAlign: 'center', padding: '1.5rem', color: '#059669' }}>All member contributions are currently fully paid!</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Report View 3: Payout Records */}
              {selectedReportType === 'PAYOUTS' && (
                <div>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                    Completed & Pending Payout Disbursements
                  </h3>
                  <table className="org-table">
                    <thead>
                      <tr>
                        <th>Recipient</th>
                        <th>Disbursed Amount</th>
                        <th>Status</th>
                        <th>Settlement</th>
                        <th>Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(reportData?.payout_records || []).map((p) => (
                        <tr key={p.id}>
                          <td style={{ fontWeight: 700 }}>{p.recipient_name}</td>
                          <td style={{ fontWeight: 800 }}>ETB {Number(p.amount_etb).toLocaleString()}</td>
                          <td><span className={`org-badge ${p.status === 'COMPLETED' ? 'org-badge-blue' : 'org-badge-green'}`}>{p.status}</span></td>
                          <td>{p.settlement_status}</td>
                          <td>{new Date(p.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                      {(!reportData?.payout_records || reportData.payout_records.length === 0) && (
                        <tr><td colSpan="5" style={{ textAlign: 'center', padding: '1.5rem', color: '#64748b' }}>No payout records logged for this group yet.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Report View 4: Treasurer Activity */}
              {selectedReportType === 'TREASURER' && (
                <div>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                    Treasurer Assignment & Financial Audits
                  </h3>
                  {reportData?.treasurer_activity ? (
                    <div style={{ padding: '1.25rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', maxWidth: '500px' }}>
                      <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Assigned Group Treasurer</div>
                      <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#0f172a', margin: '0.25rem 0' }}>{reportData.treasurer_activity.name}</div>
                      <div style={{ fontSize: '0.82rem', color: '#475569' }}>Email: {reportData.treasurer_activity.email}</div>
                      <div style={{ fontSize: '0.82rem', color: '#475569' }}>Assigned On: {new Date(reportData.treasurer_activity.assigned_at).toLocaleDateString()}</div>
                      <div style={{ marginTop: '0.75rem' }}>
                        <span className="org-badge org-badge-green">{reportData.treasurer_activity.status}</span>
                      </div>
                    </div>
                  ) : (
                    <div style={{ padding: '1.5rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', color: '#64748b' }}>
                      No Treasurer assigned to this group yet. You can assign one from the Members tab.
                    </div>
                  )}
                </div>
              )}

              {/* Report View 5: Monthly Financial Summary */}
              {selectedReportType === 'MONTHLY' && (
                <div>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '0.75rem' }}>
                    Monthly Financial Cycle & Collection Velocity
                  </h3>
                  <table className="org-table">
                    <thead>
                      <tr>
                        <th>Cycle Period</th>
                        <th>Start Date</th>
                        <th>Due Date</th>
                        <th>Expected Total</th>
                        <th>Collected Total</th>
                        <th>Cycle Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(reportData?.monthly_financial_summary || []).map((m) => (
                        <tr key={m.period_number}>
                          <td style={{ fontWeight: 700 }}>Period #{m.period_number}</td>
                          <td>{m.start_date}</td>
                          <td>{m.due_date}</td>
                          <td>ETB {Number(m.expected_etb).toLocaleString()}</td>
                          <td style={{ fontWeight: 600 }}>ETB {Number(m.collected_etb).toLocaleString()}</td>
                          <td><span className={`org-badge ${m.status === 'OPEN' ? 'org-badge-green' : 'org-badge-blue'}`}>{m.status}</span></td>
                        </tr>
                      ))}
                      {(!reportData?.monthly_financial_summary || reportData.monthly_financial_summary.length === 0) && (
                        <tr><td colSpan="6" style={{ textAlign: 'center', padding: '1.5rem', color: '#64748b' }}>No cycle periods defined yet.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB 8: VERIFICATION STATUS MODULE */}
          {activeTab === 'verification' && (
            <div className="org-card">
              <div className="org-card-header">
                <div>
                  <h2 className="org-card-title">
                    {t('orgNavVerification') || 'Organizer & Group Verification Status'}
                  </h2>
                  <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                    Multi-tier compliance: Identity verification, Equb charter verification, and commercial trade licensing.
                  </p>
                </div>
                <button
                  type="button"
                  className="org-btn-primary"
                  onClick={() => setShowVerificationModal(true)}
                >
                  Submit Verification Documents
                </button>
              </div>

              {/* Status Banner */}
              {(() => {
                const vStatus = verificationData?.profile_details?.verification_status || verificationData?.organizer_identity?.status || 'PENDING';
                if (vStatus === 'REJECTED') {
                  return (
                    <div style={{ margin: '1rem 0', padding: '1rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', color: '#b91c1c' }}>
                      <div style={{ fontWeight: 800, fontSize: '0.95rem', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <AlertCircle size={18} /> Verification Application Rejected
                      </div>
                      <div style={{ fontSize: '0.82rem', marginBottom: '0.5rem' }}>
                        <strong>Reason:</strong> {verificationData?.profile_details?.rejection_reason || 'Incomplete or unreadable legal documentation provided.'}
                      </div>
                      {verificationData?.profile_details?.admin_notes && (
                        <div style={{ fontSize: '0.8rem', background: '#ffffff', padding: '0.5rem', borderRadius: '4px', border: '1px solid #fca5a5' }}>
                          <strong>Admin Feedback:</strong> {verificationData.profile_details.admin_notes}
                        </div>
                      )}
                      <button
                        type="button"
                        className="org-btn-primary"
                        style={{ marginTop: '0.75rem', background: '#dc2626', fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                        onClick={() => setShowVerificationModal(true)}
                      >
                        Submit Corrected Documents
                      </button>
                    </div>
                  );
                } else if (vStatus === 'APPROVED' || vStatus === 'VERIFIED') {
                  return (
                    <div style={{ margin: '1rem 0', padding: '1rem', background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: '8px', color: '#047857', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <CheckCircle2 size={20} />
                      <div>
                        <div style={{ fontWeight: 800, fontSize: '0.95rem' }}>Verified & Approved Organizer Account</div>
                        <div style={{ fontSize: '0.82rem' }}>Your commercial license, business documents, and Equb operations have been reviewed and approved by Platform Super Administrators.</div>
                      </div>
                    </div>
                  );
                } else {
                  return (
                    <div style={{ margin: '1rem 0', padding: '1rem', background: '#fffbeb', border: '1px solid #fde68a', borderRadius: '8px', color: '#92400e', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <Clock size={20} />
                      <div>
                        <div style={{ fontWeight: 800, fontSize: '0.95rem' }}>Verification Pending Review (Awaiting Super Admin Approval)</div>
                        <div style={{ fontSize: '0.82rem' }}>Your verification documents have been submitted. An authorized Super Administrator is evaluating your credentials according to regulatory policies.</div>
                      </div>
                    </div>
                  );
                }
              })()}

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem', marginTop: '1rem' }}>
                {/* 1. Identity & Business Details */}
                <div style={{ padding: '1.25rem', background: '#f8fafc', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>1. Commercial Business Profile</h3>
                    <span className={`org-badge ${verificationData?.profile_details?.verification_status === 'APPROVED' ? 'org-badge-green' : verificationData?.profile_details?.verification_status === 'REJECTED' ? 'org-badge-red' : 'org-badge-orange'}`}>
                      {verificationData?.profile_details?.verification_status || 'PENDING'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.82rem', color: '#334155' }}>
                    <div><strong>Business Name:</strong> {verificationData?.profile_details?.business_name || 'N/A'}</div>
                    <div><strong>Business Type:</strong> {verificationData?.profile_details?.business_type || 'Sole Proprietorship'}</div>
                    <div><strong>Address:</strong> {verificationData?.profile_details?.business_address || 'Addis Ababa, Ethiopia'}</div>
                    <div><strong>License Number:</strong> {verificationData?.profile_details?.license_number || 'ET-MKT-PENDING'}</div>
                    <div><strong>License Issue Date:</strong> {verificationData?.profile_details?.license_issue_date || 'N/A'}</div>
                    <div><strong>License Expiry Date:</strong> {verificationData?.profile_details?.license_expiry_date || 'N/A'}</div>
                  </div>
                </div>

                {/* 2. Required Legal Documents Checklist */}
                <div style={{ padding: '1.25rem', background: '#f8fafc', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>2. Required Compliance Documents</h3>
                    <span className="org-badge org-badge-blue">Checklist</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.82rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <CheckCircle2 size={16} color="#059669" />
                      <span>Ethiopian Kebele ID / National ID / Passport</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <CheckCircle2 size={16} color="#059669" />
                      <span>Commercial Market License (Ministry of Trade)</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <CheckCircle2 size={16} color="#059669" />
                      <span>Taxpayer Identification Number (TIN) Certificate</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <CheckCircle2 size={16} color="#059669" />
                      <span>Equb Group Charter & Payout Rotation Bylaws</span>
                    </div>
                  </div>
                  <div style={{ marginTop: '0.85rem', padding: '0.5rem', background: '#eff6ff', borderRadius: '6px', fontSize: '0.72rem', color: '#1e40af' }}>
                    🛡️ <strong>Security Rule:</strong> Organizers cannot approve their own verification. All decisions are audited and finalized by authorized Super Administrators.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 9: SETTINGS MODULE */}
          {activeTab === 'settings' && (
            <div className="org-card">
              <div className="org-card-header">
                <div>
                  <h2 className="org-card-title">
                    {t('orgNavSettings') || 'Organizer Account & Security Settings'}
                  </h2>
                  <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                    Manage your personal organizer profile, credentials, notification channels, and localization.
                  </p>
                </div>
              </div>

              <form onSubmit={handleSaveSettings} style={{ maxWidth: '640px', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {/* Organizer Profile Photo & Information */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', padding: '1.25rem', background: 'var(--org-card-bg, #ffffff)', borderRadius: '12px', border: '1px solid var(--org-border, #e2e8f0)', flexWrap: 'wrap' }}>
                  <div style={{ position: 'relative', width: '70px', height: '70px', borderRadius: '50%', overflow: 'hidden', border: '2px solid #2563eb', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#eff6ff' }}>
                    {settingsForm.avatar ? (
                      <img src={settingsForm.avatar} alt="Profile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#2563eb' }}>
                        {organizerName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'OR'}
                      </span>
                    )}
                  </div>
                  <div style={{ flex: 1, minWidth: '220px' }}>
                    <div style={{ fontSize: '0.98rem', fontWeight: 800, color: 'var(--org-text-main, #0f172a)' }}>{organizerName}</div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--org-text-muted, #64748b)', marginBottom: '0.65rem' }}>
                      Verified Equb Organizer • {user?.email}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                      <label className="org-btn-primary" style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
                        <Camera size={14} />
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
                                (dataUrl) => setSettingsForm(prev => ({ ...prev, avatar: dataUrl })),
                                (errMsg) => setError(errMsg)
                              );
                            }
                          }}
                        />
                      </label>
                      {settingsForm.avatar && (
                        <button
                          type="button"
                          className="org-btn-secondary"
                          style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem', color: '#ef4444' }}
                          onClick={() => setSettingsForm(prev => ({ ...prev, avatar: '' }))}
                        >
                          Remove Photo
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                <div className="org-form-group">
                  <label className="org-label">Full Name *</label>
                  <input
                    type="text"
                    required
                    className="org-input"
                    value={settingsForm.full_name}
                    onChange={(e) => setSettingsForm({ ...settingsForm, full_name: e.target.value })}
                  />
                </div>

                <div className="org-form-group">
                  <label className="org-label">Organizer Account Email (Read-Only)</label>
                  <input
                    type="email"
                    className="org-input"
                    value={settingsForm.email || user?.email || ''}
                    disabled
                    readOnly
                    style={{ background: 'var(--bg-secondary, #f1f5f9)', cursor: 'not-allowed', opacity: 0.8 }}
                  />
                  <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.25rem' }}>
                    Primary identifier permanently tied to your organizer account identity. Email cannot be changed.
                  </div>
                </div>

                <div className="org-form-group">
                  <label className="org-label">Phone Number</label>
                  <input
                    type="text"
                    className="org-input"
                    placeholder="+251 91 123 4567"
                    value={settingsForm.phone_number}
                    onChange={(e) => setSettingsForm({ ...settingsForm, phone_number: e.target.value })}
                  />
                </div>

                <div className="org-form-group">
                  <label className="org-label">Interface & Notification Language</label>
                  <select
                    className="org-select"
                    value={settingsForm.preferred_language}
                    onChange={(e) => {
                      setSettingsForm({ ...settingsForm, preferred_language: e.target.value });
                      setLanguage(e.target.value);
                    }}
                  >
                    <option value="en">English (US)</option>
                    <option value="am">አማርኛ (Amharic)</option>
                    <option value="om">Afaan Oromoo (Oromo)</option>
                    <option value="ti">ትግርኛ (Tigrinya)</option>
                  </select>
                </div>

                {/* Notification Channels */}
                <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.6rem', color: '#0f172a' }}>
                    Notification Channels
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={settingsForm.notify_in_app}
                        onChange={(e) => setSettingsForm({ ...settingsForm, notify_in_app: e.target.checked })}
                      />
                      <span>In-App alerts (disputes, rule proposals, cash receipts)</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={settingsForm.notify_email}
                        onChange={(e) => setSettingsForm({ ...settingsForm, notify_email: e.target.checked })}
                      />
                      <span>Email summaries & billing renewal reminders</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.82rem', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={settingsForm.notify_sms}
                        onChange={(e) => setSettingsForm({ ...settingsForm, notify_sms: e.target.checked })}
                      />
                      <span>SMS contribution notifications via Ethio Telecom provider</span>
                    </label>
                  </div>
                </div>

                {/* Password Change Box */}
                <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.88rem', cursor: 'pointer', marginBottom: settingsForm.change_password ? '0.75rem' : '0' }}>
                    <input
                      type="checkbox"
                      checked={settingsForm.change_password}
                      onChange={(e) => setSettingsForm({ ...settingsForm, change_password: e.target.checked })}
                    />
                    <span>Change Account Password</span>
                  </label>

                  {settingsForm.change_password && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
                      <div>
                        <label className="org-label">Current Password *</label>
                        <input
                          type="password"
                          required
                          className="org-input"
                          value={settingsForm.current_password}
                          onChange={(e) => setSettingsForm({ ...settingsForm, current_password: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="org-label">New Password (min 8 characters) *</label>
                        <input
                          type="password"
                          required
                          className="org-input"
                          value={settingsForm.new_password}
                          onChange={(e) => setSettingsForm({ ...settingsForm, new_password: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="org-label">Confirm New Password *</label>
                        <input
                          type="password"
                          required
                          className="org-input"
                          value={settingsForm.confirm_new_password}
                          onChange={(e) => setSettingsForm({ ...settingsForm, confirm_new_password: e.target.value })}
                        />
                      </div>
                    </div>
                  )}
                </div>

                <div style={{ padding: '0.65rem 0.85rem', background: '#eff6ff', borderRadius: '6px', border: '1px solid #bfdbfe', fontSize: '0.75rem', color: '#1e40af' }}>
                  🔒 <strong>Governance Notice:</strong> Organizers can manage their own personal preferences. System-wide platform settings and payment gateway configurations are reserved for Platform Super Administrators.
                </div>

                <button
                  type="submit"
                  disabled={settingsSaving}
                  className="org-btn-primary"
                  style={{ alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  {settingsSaving ? 'Saving Changes...' : 'Save Settings'}
                </button>
              </form>
            </div>
          )}

          {/* TAB 10: HELP & SUPPORT MODULE */}
          {activeTab === 'support' && (
            <div className="org-card">
              <div className="org-card-header">
                <div>
                  <h2 className="org-card-title">
                    {t('orgNavSupport') || 'Help & Support Center'}
                  </h2>
                  <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                    Knowledge base, FAQ articles, and direct ticketing with Platform Super Admins.
                  </p>
                </div>
                <button
                  type="button"
                  className="org-btn-primary"
                  onClick={() => setShowSupportTicketModal(true)}
                >
                  + Submit Support Ticket
                </button>
              </div>

              {/* FAQs */}
              <div style={{ marginBottom: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Frequently Asked Questions</h3>
                <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                    How does dual confirmation work for cash contributions?
                  </div>
                  <div style={{ fontSize: '0.82rem', color: '#475569' }}>
                    When a Treasurer records cash in-hand, the payment remains in PENDING_VERIFICATION until the Group Organizer confirms receipt. Only then is it credited to the financial ledger.
                  </div>
                </div>

                <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '0.25rem' }}>
                    How are dispute escalations handled?
                  </div>
                  <div style={{ fontSize: '0.82rem', color: '#475569' }}>
                    Organizers can resolve disputes directly or click Escalate. Escalated disputes immediately notify the Platform Super Admin team with full audit logs.
                  </div>
                </div>
              </div>

              {/* Ticket History */}
              <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                Your Submitted Support Inquiries
              </h3>
              <table className="org-table">
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {(supportTickets.length > 0 ? supportTickets : [
                    { id: '1', subject: 'Question regarding CBE Birr bulk payout integration', category: 'TECHNICAL', status: 'OPEN', created_at: new Date().toISOString() }
                  ]).map((tk) => (
                    <tr key={tk.id}>
                      <td style={{ fontWeight: 700 }}>{tk.subject}</td>
                      <td>{tk.category}</td>
                      <td>
                        <span className="org-badge org-badge-orange">{tk.status}</span>
                      </td>
                      <td>{new Date(tk.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </main>
      </div>

      {/* MODAL 1: Create Group Modal */}
      {showCreateGroupModal && (
        <div className="org-modal-overlay">
          <div className="org-modal">
            <div className="org-modal-header">
              <div className="org-modal-title">{t('orgCreateGroup') || 'Create New Equb Group'}</div>
              <button type="button" className="org-menu-btn" onClick={() => setShowCreateGroupModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleCreateGroup}>
              <div className="org-modal-body">
                <div className="org-form-group">
                  <label className="org-label">Group Name *</label>
                  <input
                    type="text"
                    className="org-input"
                    required
                    value={createGroupForm.name}
                    onChange={(e) => setCreateGroupForm({ ...createGroupForm, name: e.target.value })}
                    placeholder="e.g. Merkato Merchants Equb"
                  />
                </div>
                <div className="org-form-group">
                  <label className="org-label">Purpose / Category</label>
                  <input
                    type="text"
                    className="org-input"
                    value={createGroupForm.group_purpose}
                    onChange={(e) => setCreateGroupForm({ ...createGroupForm, group_purpose: e.target.value })}
                    placeholder="e.g. Business Working Capital"
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div className="org-form-group">
                    <label className="org-label">Contribution Amount (ETB) *</label>
                    <input
                      type="number"
                      className="org-input"
                      required
                      min="100"
                      value={createGroupForm.contribution_amount}
                      onChange={(e) => setCreateGroupForm({ ...createGroupForm, contribution_amount: e.target.value })}
                    />
                  </div>
                  <div className="org-form-group">
                    <label className="org-label">Frequency *</label>
                    <select
                      className="org-select"
                      value={createGroupForm.contribution_frequency}
                      onChange={(e) => setCreateGroupForm({ ...createGroupForm, contribution_frequency: e.target.value })}
                    >
                      <option value="WEEKLY">Weekly</option>
                      <option value="BIWEEKLY">Biweekly</option>
                      <option value="MONTHLY">Monthly</option>
                    </select>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div className="org-form-group">
                    <label className="org-label">Member Capacity *</label>
                    <input
                      type="number"
                      className="org-input"
                      required
                      min="2"
                      max="100"
                      value={createGroupForm.capacity}
                      onChange={(e) => setCreateGroupForm({ ...createGroupForm, capacity: parseInt(e.target.value, 10) })}
                    />
                  </div>
                  <div className="org-form-group">
                    <label className="org-label">Start Date *</label>
                    <input
                      type="date"
                      className="org-input"
                      required
                      value={createGroupForm.start_date}
                      onChange={(e) => setCreateGroupForm({ ...createGroupForm, start_date: e.target.value })}
                    />
                  </div>
                </div>

                {/* Dropdown 1: Lottery Method & Grace Period */}
                <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '0.75rem' }}>
                  <div className="org-form-group">
                    <label className="org-label">Lottery Method * (Dropdown 1)</label>
                    <select
                      className="org-select"
                      value={createGroupForm.lottery_method}
                      onChange={(e) => setCreateGroupForm({ ...createGroupForm, lottery_method: e.target.value })}
                    >
                      <option value="METHOD_A">Option A – One-time lottery</option>
                      <option value="METHOD_B">Option B – Round-by-round lottery</option>
                    </select>
                    <div style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '0.25rem' }}>
                      {createGroupForm.lottery_method === 'METHOD_A'
                        ? 'Option A: Conduct one lottery at cycle start to determine full payout order for all eligible members.'
                        : 'Option B: Conduct separate lottery draw each round from remaining eligible non-winners.'}
                    </div>
                  </div>
                  <div className="org-form-group">
                    <label className="org-label">Grace Period (Days) *</label>
                    <input
                      type="number"
                      className="org-input"
                      required
                      min="0"
                      max="30"
                      value={createGroupForm.grace_period_days}
                      onChange={(e) => setCreateGroupForm({ ...createGroupForm, grace_period_days: parseInt(e.target.value, 10) || 0 })}
                    />
                    <div style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '0.25rem' }}>
                      Days after due date before overdue case opens.
                    </div>
                  </div>
                </div>

                <div className="org-form-group">
                  <label className="org-label">Equb Charter Terms</label>
                  <textarea
                    className="org-textarea"
                    rows="3"
                    value={createGroupForm.rules_terms}
                    onChange={(e) => setCreateGroupForm({ ...createGroupForm, rules_terms: e.target.value })}
                    placeholder="Specify contribution deadline, dual cash verification rule, rotation policy..."
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', padding: '0.85rem', background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe' }}>
                  <input
                    type="checkbox"
                    id="participate_as_member"
                    checked={createGroupForm.participate_as_member}
                    onChange={(e) => setCreateGroupForm({ ...createGroupForm, participate_as_member: e.target.checked })}
                    style={{ marginTop: '0.2rem', width: '16px', height: '16px', accentColor: '#2563eb', cursor: 'pointer' }}
                  />
                  <label htmlFor="participate_as_member" style={{ fontSize: '0.85rem', color: '#1e40af', cursor: 'pointer' }}>
                    <strong>Participate as a contributing member</strong>
                    <div style={{ fontSize: '0.78rem', color: '#3b82f6', marginTop: '0.15rem' }}>
                      Enroll me into the rotation schedule (#1) and generate my periodic contribution obligations so I can save alongside members.
                    </div>
                  </label>
                </div>
              </div>
              <div className="org-modal-footer">
                <button type="button" className="org-btn-secondary" onClick={() => setShowCreateGroupModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="org-btn-primary">
                  Create Equb Group
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Invite Member Modal */}
      {showInviteModal && (
        <div className="org-modal-overlay">
          <div className="org-modal">
            <div className="org-modal-header">
              <div className="org-modal-title">Invite Member to {selectedGroup?.name}</div>
              <button type="button" className="org-menu-btn" onClick={() => setShowInviteModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleInviteMember}>
              <div className="org-modal-body">
                <div className="org-form-group">
                  <label className="org-label">Prospective Member Email *</label>
                  <input
                    type="email"
                    className="org-input"
                    required
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="member@example.com"
                  />
                </div>
                {inviteResult && (
                  <div style={{ padding: '0.75rem', background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe', fontSize: '0.82rem' }}>
                    <div style={{ fontWeight: 700, color: '#1d4ed8', marginBottom: '0.25rem' }}>
                      Secure Invitation Link Generated:
                    </div>
                    <code style={{ wordBreak: 'break-all', display: 'block', background: '#ffffff', padding: '0.4rem', borderRadius: '4px' }}>
                      {window.location.origin}{inviteResult.invite_url}
                    </code>
                  </div>
                )}
              </div>
              <div className="org-modal-footer">
                <button type="button" className="org-btn-secondary" onClick={() => { setShowInviteModal(false); setInviteResult(null); }}>
                  Close
                </button>
                <button type="submit" className="org-btn-primary">
                  Generate Invitation Link
                </button>
              </div>
            </form>
          </div>
        </div>
      )}



      {/* MODAL 3: Assign Treasurer Modal */}
      {showAssignTreasurerModal && (
        <div className="org-modal-overlay">
          <div className="org-modal">
            <div className="org-modal-header">
              <div className="org-modal-title">Assign Treasurer for {selectedGroup?.name}</div>
              <button type="button" className="org-menu-btn" onClick={() => setShowAssignTreasurerModal(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="org-modal-body">
              <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                Select an active group member to serve as the group's Treasurer for cash recording and bank reconciliation.
              </p>
              <div className="org-form-group">
                <label className="org-label">Eligible Member</label>
                <select
                  className="org-select"
                  value={selectedTreasurerMemberId}
                  onChange={(e) => setSelectedTreasurerMemberId(e.target.value)}
                >
                  <option value="">-- Choose Eligible Member --</option>
                  {(treasurerInfo?.eligible_members || groupMembers).map((m) => (
                    <option key={m.membership_id} value={m.membership_id}>
                      {m.full_name} ({m.email})
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="org-modal-footer">
              <button type="button" className="org-btn-secondary" onClick={() => setShowAssignTreasurerModal(false)}>
                Cancel
              </button>
              <button type="button" className="org-btn-primary" onClick={handleAssignTreasurer}>
                Confirm Assignment
              </button>
            </div>
          </div>
        </div>
      )}



      {/* MODAL 4: Schedule Payout Modal */}
      {showSchedulePayoutModal && (
        <div className="org-modal-overlay">
          <div className="org-modal">
            <div className="org-modal-header">
              <div className="org-modal-title">Schedule Payout for {selectedGroup?.name}</div>
              <button type="button" className="org-menu-btn" onClick={() => setShowSchedulePayoutModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSchedulePayout}>
              <div className="org-modal-body">
                <div className="org-form-group">
                  <label className="org-label">Eligible Recipient Member *</label>
                  <select
                    className="org-select"
                    required
                    value={payoutForm.recipient_membership_id}
                    onChange={(e) => setPayoutForm({ ...payoutForm, recipient_membership_id: e.target.value })}
                  >
                    <option value="">-- Choose Recipient --</option>
                    {groupMembers.map((m) => (
                      <option key={m.membership_id} value={m.membership_id}>
                        {m.full_name} (#{m.payout_order_index})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="org-form-group">
                  <label className="org-label">Disbursement Amount (ETB)</label>
                  <input
                    type="number"
                    className="org-input"
                    value={payoutForm.amount}
                    onChange={(e) => setPayoutForm({ ...payoutForm, amount: e.target.value })}
                    placeholder="Leave blank for full group pool"
                  />
                </div>
                <div className="org-form-group">
                  <label className="org-label">Coordination Notes</label>
                  <textarea
                    className="org-textarea"
                    rows="2"
                    value={payoutForm.notes}
                    onChange={(e) => setPayoutForm({ ...payoutForm, notes: e.target.value })}
                    placeholder="e.g. Scheduled rotation round"
                  />
                </div>
              </div>
              <div className="org-modal-footer">
                <button type="button" className="org-btn-secondary" onClick={() => setShowSchedulePayoutModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="org-btn-primary">
                  Confirm Schedule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}



      {/* MODAL 5: Support Ticket Modal */}
      {showSupportTicketModal && (
        <div className="org-modal-overlay">
          <div className="org-modal">
            <div className="org-modal-header">
              <div className="org-modal-title">Submit Support Ticket to Super Admin</div>
              <button type="button" className="org-menu-btn" onClick={() => setShowSupportTicketModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSupportTicketSubmit}>
              <div className="org-modal-body">
                <div className="org-form-group">
                  <label className="org-label">Subject *</label>
                  <input
                    type="text"
                    className="org-input"
                    required
                    value={supportTicketForm.subject}
                    onChange={(e) => setSupportTicketForm({ ...supportTicketForm, subject: e.target.value })}
                    placeholder="Brief description of the request"
                  />
                </div>
                <div className="org-form-group">
                  <label className="org-label">Category</label>
                  <select
                    className="org-select"
                    value={supportTicketForm.category}
                    onChange={(e) => setSupportTicketForm({ ...supportTicketForm, category: e.target.value })}
                  >
                    <option value="TECHNICAL">Technical Issue</option>
                    <option value="BILLING">Billing & Subscription</option>
                    <option value="DISPUTE_ESCALATION">Dispute Escalation</option>
                    <option value="VERIFICATION">Verification Inquiries</option>
                    <option value="OTHER">General Inquiries</option>
                  </select>
                </div>
                <div className="org-form-group">
                  <label className="org-label">Message *</label>
                  <textarea
                    className="org-textarea"
                    rows="4"
                    required
                    value={supportTicketForm.message}
                    onChange={(e) => setSupportTicketForm({ ...supportTicketForm, message: e.target.value })}
                    placeholder="Provide full details regarding the inquiry..."
                  />
                </div>
              </div>
              <div className="org-modal-footer">
                <button type="button" className="org-btn-secondary" onClick={() => setShowSupportTicketModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="org-btn-primary">
                  Submit Ticket
                </button>
              </div>
            </form>
          </div>
        </div>
      )}



      {/* MODAL 6: Verification Document Modal */}
      {showVerificationModal && (
        <div className="org-modal-overlay">
          <div className="org-modal">
            <div className="org-modal-header">
              <div className="org-modal-title">Submit Verification Documents</div>
              <button type="button" className="org-menu-btn" onClick={() => setShowVerificationModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleVerificationSubmit}>
              <div className="org-modal-body">
                <p style={{ fontSize: '0.82rem', color: '#64748b' }}>
                  Upload or provide notes regarding your trade license, Kebele ID, or commercial registration for Super Admin approval.
                </p>
                <div className="org-form-group">
                  <label className="org-label">Document Details / Submission Notes *</label>
                  <textarea
                    className="org-textarea"
                    rows="4"
                    required
                    value={verificationNotes}
                    onChange={(e) => setVerificationNotes(e.target.value)}
                    placeholder="e.g. Attached Trade License #12345/2016 and Kebele ID from Kirkos Sub-City..."
                  />
                </div>
              </div>
              <div className="org-modal-footer">
                <button type="button" className="org-btn-secondary" onClick={() => setShowVerificationModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="org-btn-primary">
                  Submit for Review
                </button>
              </div>
            </form>
          </div>
        </div>
      )}



      {/* MODAL 7: Group Details Drawer / Modal */}
      {showGroupDetailsModal && selectedGroup && (
        <div className="org-modal-overlay">
          <div className="org-modal" style={{ maxWidth: '750px' }}>
            <div className="org-modal-header">
              <div className="org-modal-title">{selectedGroup.name} — Full Details</div>
              <button type="button" className="org-menu-btn" onClick={() => setShowGroupDetailsModal(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="org-modal-body">
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1rem' }}>
                <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Status</div>
                  <div style={{ fontWeight: 800 }}>{selectedGroup.status}</div>
                </div>
                <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Contribution</div>
                  <div style={{ fontWeight: 800 }}>ETB {Number(selectedGroup.contribution_amount).toLocaleString()}</div>
                </div>
                <div style={{ padding: '0.75rem', background: '#f8fafc', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Capacity</div>
                  <div style={{ fontWeight: 800 }}>{selectedGroup.capacity} members</div>
                </div>
              </div>

              <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.35rem' }}>Active Group Rules Charter</h4>
              <p style={{ fontSize: '0.82rem', color: '#475569', background: '#f1f5f9', padding: '0.75rem', borderRadius: '6px' }}>
                {groupRules[0]?.terms_text || 'Standard rotation equb charter. Mandatory timely contributions.'}
              </p>

              {/* Chapa Subaccount Info inside Details */}
              <div style={{ marginTop: '0.85rem', padding: '0.85rem', background: selectedGroup.chapa_subaccount_id ? '#f0fdf4' : '#f8fafc', borderRadius: '8px', border: `1px solid ${selectedGroup.chapa_subaccount_id ? '#86efac' : '#e2e8f0'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 800, fontSize: '0.85rem', color: selectedGroup.chapa_subaccount_id ? '#15803d' : '#334155' }}>
                    <Landmark size={16} /> Chapa Subaccount Bank Settlement
                  </div>
                  <button
                    type="button"
                    className="org-btn-view-pill"
                    style={{ color: '#2563eb', fontSize: '0.78rem' }}
                    onClick={() => {
                      setShowGroupDetailsModal(false);
                      handleOpenSubaccountModal(selectedGroup);
                    }}
                  >
                    {selectedGroup.chapa_subaccount_id ? 'Manage Bank' : 'Connect Bank'}
                  </button>
                </div>
                {selectedGroup.chapa_subaccount_id ? (
                  <div style={{ fontSize: '0.78rem', color: '#166534', marginTop: '0.4rem' }}>
                    Linked Bank: <strong>{selectedGroup.bank_name || 'Commercial Bank of Ethiopia'}</strong> • Account: <strong>{selectedGroup.bank_account_number}</strong> ({selectedGroup.bank_account_name || selectedGroup.name})<br />
                    Subaccount ID: <code style={{ fontSize: '0.72rem' }}>{selectedGroup.chapa_subaccount_id}</code>
                  </div>
                ) : (
                  <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '0.3rem' }}>
                    No bank linked yet. Connect your Equb's common bank account to route member contributions directly.
                  </div>
                )}
              </div>

              <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginTop: '1rem', marginBottom: '0.35rem' }}>
                Group Members ({groupMembers.length})
              </h4>
              <div style={{ maxHeight: '200px', overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
                <table className="org-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Role</th>
                      <th>Payout #</th>
                    </tr>
                  </thead>
                  <tbody>
                    {groupMembers.map((m) => (
                      <tr key={m.membership_id}>
                        <td>{m.full_name}</td>
                        <td>{m.roles?.join(', ') || 'Member'}</td>
                        <td>#{m.payout_order_index}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="org-modal-footer">
              <button type="button" className="org-btn-secondary" onClick={() => setShowGroupDetailsModal(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}



      {/* MODAL 8: Add Member Directly Modal */}
      {showAddMemberModal && selectedGroup && (
        <div className="org-modal-overlay">
          <div className="org-modal" style={{ maxWidth: '540px' }}>
            <div className="org-modal-header">
              <div className="org-modal-title">Add Member to {selectedGroup.name}</div>
              <button type="button" className="org-menu-btn" onClick={() => setShowAddMemberModal(false)}>
                <X size={18} />
              </button>
            </div>
            {addMemberResult ? (
              <div className="org-modal-body">
                <div style={{ padding: '1rem', background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: '8px', color: '#047857', marginBottom: '1rem' }}>
                  <div style={{ fontWeight: 800, fontSize: '1rem', marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <CheckCircle2 size={18} /> Member Account Created Successfully!
                  </div>
                  <div style={{ fontSize: '0.85rem' }}>
                    {addMemberResult.message}
                  </div>
                </div>

                <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '0.85rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div><strong>Full Name:</strong> {addMemberResult.user?.full_name}</div>
                  <div><strong>Email Address:</strong> {addMemberResult.user?.email}</div>
                  {addMemberResult.temporary_password && (
                    <div style={{ marginTop: '0.5rem', padding: '0.75rem', background: '#eff6ff', borderRadius: '6px', border: '1px solid #bfdbfe' }}>
                      <div style={{ fontWeight: 700, color: '#1d4ed8', marginBottom: '0.25rem' }}>
                        Temporary Password (Share with Member):
                      </div>
                      <code style={{ fontSize: '1rem', fontWeight: 800, color: '#1e3a8a', background: '#ffffff', padding: '0.25rem 0.6rem', borderRadius: '4px', border: '1px solid #93c5fd' }}>
                        {addMemberResult.temporary_password}
                      </code>
                    </div>
                  )}
                  {addMemberResult.activation_token && (
                    <div style={{ marginTop: '0.5rem', padding: '0.75rem', background: '#eff6ff', borderRadius: '6px', border: '1px solid #bfdbfe' }}>
                      <div style={{ fontWeight: 700, color: '#1d4ed8', marginBottom: '0.25rem' }}>
                        Secure Activation Token:
                      </div>
                      <code style={{ fontSize: '0.8rem', wordBreak: 'break-all' }}>
                        {addMemberResult.activation_token}
                      </code>
                    </div>
                  )}
                </div>

                <div className="org-modal-footer" style={{ marginTop: '1.25rem' }}>
                  <button
                    type="button"
                    className="org-btn-primary"
                    onClick={() => {
                      setShowAddMemberModal(false);
                      setAddMemberResult(null);
                    }}
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleAddMember}>
                <div className="org-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                  {!groupMembers.some((m) => (m.email === user?.email || (user?.id && String(m.user_id) === String(user.id))) && (m.roles?.some(r => String(r).toLowerCase().includes('member')) || m.roles?.includes('GROUP_MEMBER'))) && (
                    <div style={{ padding: '0.85rem', background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
                      <div>
                        <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#1e40af' }}>
                          Add Yourself as a Member?
                        </div>
                        <div style={{ fontSize: '0.78rem', color: '#3b82f6' }}>
                          You can quickly enroll yourself ({user?.full_name || 'Organizer'}) as a participating member to save and receive rotating payouts.
                        </div>
                      </div>
                      <button
                        type="button"
                        className="org-btn-primary"
                        style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', whiteSpace: 'nowrap', background: '#2563eb' }}
                        onClick={async () => {
                          setShowAddMemberModal(false);
                          await handleJoinSelectedGroupAsMember();
                        }}
                      >
                        Enroll Myself
                      </button>
                    </div>
                  )}

                  <p style={{ fontSize: '0.82rem', color: '#64748b', margin: 0 }}>
                    Create an authorized member account directly for this Equb group. The member will be able to log in to the Member Interface.
                  </p>

                  <div className="org-form-group">
                    <label className="org-label">Full Legal Name *</label>
                    <input
                      type="text"
                      required
                      className="org-input"
                      placeholder="e.g. Almaz Tadesse"
                      value={addMemberForm.full_name}
                      onChange={(e) => setAddMemberForm({ ...addMemberForm, full_name: e.target.value })}
                    />
                  </div>

                  <div className="org-form-group">
                    <label className="org-label">Email Address *</label>
                    <input
                      type="email"
                      required
                      className="org-input"
                      placeholder="member@example.com"
                      value={addMemberForm.email}
                      onChange={(e) => setAddMemberForm({ ...addMemberForm, email: e.target.value })}
                    />
                  </div>

                  <div className="org-form-group">
                    <label className="org-label">Phone Number (Optional)</label>
                    <input
                      type="text"
                      className="org-input"
                      placeholder="+251 91 123 4567"
                      value={addMemberForm.phone_number}
                      onChange={(e) => setAddMemberForm({ ...addMemberForm, phone_number: e.target.value })}
                    />
                  </div>

                  <div className="org-form-group">
                    <label className="org-label">Credential Provisioning Method</label>
                    <select
                      className="org-select"
                      value={addMemberForm.password_setup_method}
                      onChange={(e) => setAddMemberForm({ ...addMemberForm, password_setup_method: e.target.value })}
                    >
                      <option value="TEMPORARY_PASSWORD">Set Temporary Password (Organizer provides)</option>
                      <option value="ACTIVATION_LINK">Generate Single-Use Activation Token</option>
                    </select>
                  </div>

                  {addMemberForm.password_setup_method === 'TEMPORARY_PASSWORD' && (
                    <div className="org-form-group">
                      <label className="org-label">Initial Password *</label>
                      <input
                        type="text"
                        required
                        className="org-input"
                        placeholder="e.g. MemberPass2026!"
                        value={addMemberForm.initial_password}
                        onChange={(e) => setAddMemberForm({ ...addMemberForm, initial_password: e.target.value })}
                      />
                    </div>
                  )}
                </div>

                <div className="org-modal-footer">
                  <button type="button" className="org-btn-secondary" onClick={() => setShowAddMemberModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="org-btn-primary" style={{ background: '#10b981' }}>
                    Create Member Account
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}



      {/* MODAL 9: Member Details & Individual Contribution History Modal */}
      {showMemberDetailModal && (
        <div className="org-modal-overlay">
          <div className="org-modal" style={{ maxWidth: '680px' }}>
            <div className="org-modal-header">
              <div className="org-modal-title">
                {selectedMemberDetail?.user?.full_name || 'Member Details & Financial Record'}
              </div>
              <button type="button" className="org-menu-btn" onClick={() => setShowMemberDetailModal(false)}>
                <X size={18} />
              </button>
            </div>

            {loadingMemberDetail ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>Loading member financial records...</div>
            ) : selectedMemberDetail ? (
              <form onSubmit={handleSaveMemberDetail}>
                <div className="org-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {/* Financial Summary Card */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', padding: '0.85rem', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Expected Total</div>
                      <div style={{ fontWeight: 800, fontSize: '1.05rem', color: '#0f172a' }}>
                        ETB {Number(selectedMemberDetail.financial_summary?.total_expected_etb || 0).toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Paid Total</div>
                      <div style={{ fontWeight: 800, fontSize: '1.05rem', color: '#059669' }}>
                        ETB {Number(selectedMemberDetail.financial_summary?.total_paid_etb || 0).toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '0.72rem', color: '#64748b' }}>Outstanding</div>
                      <div style={{ fontWeight: 800, fontSize: '1.05rem', color: selectedMemberDetail.financial_summary?.outstanding_etb > 0 ? '#dc2626' : '#059669' }}>
                        ETB {Number(selectedMemberDetail.financial_summary?.outstanding_etb || 0).toLocaleString()}
                      </div>
                    </div>
                  </div>

                  {/* Editable Details */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.85rem' }}>
                    <div className="org-form-group">
                      <label className="org-label">Full Name</label>
                      <input
                        type="text"
                        className="org-input"
                        value={memberDetailForm.full_name}
                        onChange={(e) => setMemberDetailForm({ ...memberDetailForm, full_name: e.target.value })}
                      />
                    </div>
                    <div className="org-form-group">
                      <label className="org-label">Phone Number</label>
                      <input
                        type="text"
                        className="org-input"
                        value={memberDetailForm.phone_number}
                        onChange={(e) => setMemberDetailForm({ ...memberDetailForm, phone_number: e.target.value })}
                      />
                    </div>
                    <div className="org-form-group">
                      <label className="org-label">Payout Order Index</label>
                      <input
                        type="number"
                        min="1"
                        className="org-input"
                        value={memberDetailForm.payout_order_index}
                        onChange={(e) => setMemberDetailForm({ ...memberDetailForm, payout_order_index: e.target.value })}
                      />
                    </div>
                    <div className="org-form-group">
                      <label className="org-label">Membership Status</label>
                      <select
                        className="org-select"
                        value={memberDetailForm.status}
                        onChange={(e) => setMemberDetailForm({ ...memberDetailForm, status: e.target.value })}
                      >
                        <option value="ACTIVE">Active</option>
                        <option value="SUSPENDED">Suspended (Deactivated)</option>
                        <option value="REMOVED">Removed</option>
                      </select>
                    </div>
                  </div>

                  {/* Individual Contribution Obligations */}
                  <div>
                    <h4 style={{ fontSize: '0.88rem', fontWeight: 700, marginBottom: '0.35rem' }}>
                      Individual Contribution Schedule & Obligations
                    </h4>
                    <div style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
                      <table className="org-table">
                        <thead>
                          <tr>
                            <th>Period</th>
                            <th>Due Date</th>
                            <th>Expected</th>
                            <th>Paid</th>
                            <th>Status</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(selectedMemberDetail.obligations || []).map((ob) => (
                            <tr key={ob.id}>
                              <td>#{ob.period_number || '—'}</td>
                              <td>{ob.due_date}</td>
                              <td>ETB {Number(ob.expected_amount).toLocaleString()}</td>
                              <td>ETB {Number(ob.amount_paid).toLocaleString()}</td>
                              <td><span className={`org-badge ${ob.status === 'PAID' ? 'org-badge-green' : 'org-badge-orange'}`}>{ob.status}</span></td>
                            </tr>
                          ))}
                          {(!selectedMemberDetail.obligations || selectedMemberDetail.obligations.length === 0) && (
                            <tr><td colSpan="5" style={{ textAlign: 'center', padding: '1rem', color: '#64748b' }}>No obligations logged.</td></tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                <div className="org-modal-footer">
                  <button type="button" className="org-btn-secondary" onClick={() => setShowMemberDetailModal(false)}>
                    Cancel
                  </button>
                  <button type="submit" className="org-btn-primary">
                    Save Member Changes
                  </button>
                </div>
              </form>
            ) : null}
          </div>
        </div>
      )}



      {/* MODAL 10: Edit Group Modal */}
      {showEditGroupModal && (
        <div className="org-modal-overlay">
          <div className="org-modal" style={{ maxWidth: '520px' }}>
            <div className="org-modal-header">
              <div className="org-modal-title">Edit Equb Group Details</div>
              <button type="button" className="org-menu-btn" onClick={() => setShowEditGroupModal(false)}>
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSaveEditGroup}>
              <div className="org-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div className="org-form-group">
                  <label className="org-label">Equb Group Name *</label>
                  <input
                    type="text"
                    required
                    className="org-input"
                    value={editGroupForm.name}
                    onChange={(e) => setEditGroupForm({ ...editGroupForm, name: e.target.value })}
                  />
                </div>
                <div className="org-form-group">
                  <label className="org-label">Category / Purpose</label>
                  <input
                    type="text"
                    className="org-input"
                    value={editGroupForm.group_purpose}
                    onChange={(e) => setEditGroupForm({ ...editGroupForm, group_purpose: e.target.value })}
                    placeholder="e.g. Business Equb, Family Savings"
                  />
                </div>
                <div className="org-form-group">
                  <label className="org-label">Member Capacity Limit</label>
                  <input
                    type="number"
                    min="2"
                    max="100"
                    className="org-input"
                    value={editGroupForm.capacity}
                    onChange={(e) => setEditGroupForm({ ...editGroupForm, capacity: e.target.value })}
                  />
                </div>
                <div className="org-form-group">
                  <label className="org-label">Group Description</label>
                  <textarea
                    rows="3"
                    className="org-textarea"
                    value={editGroupForm.description}
                    onChange={(e) => setEditGroupForm({ ...editGroupForm, description: e.target.value })}
                  />
                </div>
              </div>
              <div className="org-modal-footer">
                <button type="button" className="org-btn-secondary" onClick={() => setShowEditGroupModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="org-btn-primary">
                  Update Group
                </button>
              </div>
            </form>
          </div>
        </div>
      )}



      {/* MODAL 11: Chapa Group Subaccount & Settlement Modal */}
      {showSubaccountModal && selectedGroup && (
        <div className="org-modal-overlay">
          <div className="org-modal" style={{ maxWidth: '600px' }}>
            <div className="org-modal-header">
              <div className="org-modal-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Landmark size={20} color="#2563eb" /> Chapa Subaccount — {selectedGroup.name}
              </div>
              <button type="button" className="org-menu-btn" onClick={() => setShowSubaccountModal(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="org-modal-body">
              <div style={{
                padding: '0.85rem',
                background: 'var(--org-blue-light, #eff6ff)',
                borderRadius: '8px',
                border: '1px solid var(--org-border, #bfdbfe)',
                marginBottom: '1rem',
                fontSize: '0.82rem',
                color: 'var(--org-text-main, #1e40af)'
              }}>
                <div style={{ fontWeight: 700, marginBottom: '0.25rem', color: 'var(--org-blue, #2563eb)' }}>
                  🏦 Direct Member Contribution Routing to Group Bank Account
                </div>
                Connecting a Chapa Subaccount allows group members' digital contributions (Telebirr, CBE Birr, cards) to automatically route directly into this group's official bank account with <strong>0% platform deduction (100% group savings)</strong>. Platform SaaS rent remains strictly segregated.
              </div>

              {subaccountInfo && subaccountInfo.has_subaccount && (
                <div style={{
                  padding: '0.85rem',
                  background: 'var(--org-green-light, #ecfdf5)',
                  borderRadius: '8px',
                  border: '1px solid #10b981',
                  marginBottom: '1.25rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 800, color: '#10b981', fontSize: '0.9rem' }}>
                    <CheckCircle2 size={16} /> Chapa Subaccount Connected & Active
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem', marginTop: '0.5rem', fontSize: '0.8rem', color: 'var(--org-text-main, #166534)' }}>
                    <div><strong>Bank:</strong> {subaccountInfo.bank_name || 'Bank'}</div>
                    <div><strong>Account #:</strong> {subaccountInfo.bank_account_number}</div>
                    <div><strong>Holder:</strong> {subaccountInfo.bank_account_name}</div>
                    <div><strong>Subaccount ID:</strong> <span style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>{subaccountInfo.chapa_subaccount_id?.slice(0, 16)}...</span></div>
                  </div>
                </div>
              )}

              <form onSubmit={handleLinkSubaccount}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                  <div>
                    <label className="org-label" style={{ display: 'block', marginBottom: '0.35rem' }}>
                      Select Bank / Mobile Money Wallet *
                    </label>
                    <select
                      className="org-input"
                      value={subaccountForm.bank_code}
                      onChange={(e) => {
                        const code = e.target.value;
                        const bObj = supportedBanks.find(b => String(b.id) === String(code));
                        setSubaccountForm(prev => ({
                          ...prev,
                          bank_code: code,
                          bank_name: bObj ? bObj.name : prev.bank_name
                        }));
                      }}
                      required
                    >
                      {supportedBanks.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.name} (Code: {b.id})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="org-label" style={{ display: 'block', marginBottom: '0.35rem' }}>
                      Account Holder / Committee Name *
                    </label>
                    <input
                      type="text"
                      className="org-input"
                      placeholder="e.g. Merkato Equb Common Fund"
                      value={subaccountForm.account_name}
                      onChange={(e) => setSubaccountForm({ ...subaccountForm, account_name: e.target.value })}
                      required
                    />
                  </div>

                  <div>
                    <label className="org-label" style={{ display: 'block', marginBottom: '0.35rem' }}>
                      Bank Account / Mobile Money Number *
                    </label>
                    <input
                      type="text"
                      className="org-input"
                      placeholder="e.g. 1000123456789 or 0911234567"
                      value={subaccountForm.account_number}
                      onChange={(e) => setSubaccountForm({ ...subaccountForm, account_number: e.target.value })}
                      required
                    />
                  </div>

                  <div>
                    <label className="org-label" style={{ display: 'block', marginBottom: '0.35rem' }}>
                      Equb Business / Display Name
                    </label>
                    <input
                      type="text"
                      className="org-input"
                      placeholder={selectedGroup.name}
                      value={subaccountForm.business_name}
                      onChange={(e) => setSubaccountForm({ ...subaccountForm, business_name: e.target.value })}
                    />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '1rem' }}>
                    <button
                      type="button"
                      className="org-btn-secondary"
                      onClick={() => setShowSubaccountModal(false)}
                      disabled={subaccountLoading}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="org-btn-primary"
                      disabled={subaccountLoading}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                    >
                      {subaccountLoading ? <RefreshCw className="org-spin" size={16} /> : <CheckCircle2 size={16} />}
                      {subaccountInfo && subaccountInfo.has_subaccount ? 'Update Chapa Subaccount' : 'Connect Chapa Subaccount'}
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}



      {/* MODAL 12: Make Personal Contribution Payment Modal */}
      {showPersonalPaymentModal && selectedPersonalObligation && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}>
          <div style={{ background: '#fff', borderRadius: '16px', maxWidth: '520px', width: '100%', padding: '1.75rem', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.2rem', fontWeight: 800, color: '#0f172a' }}>Make Contribution Payment</h3>
              <button type="button" onClick={() => setShowPersonalPaymentModal(false)} style={{ border: 'none', background: 'none', cursor: 'pointer', color: '#64748b' }}>
                <X size={20} />
              </button>
            </div>

            <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '10px', marginBottom: '1.25rem', border: '1px solid #e2e8f0' }}>
              <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Group: <strong>{selectedPersonalObligation.group_name}</strong></div>
              <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#0f172a', margin: '0.35rem 0' }}>
                ETB {Number(selectedPersonalObligation.remaining_amount || selectedPersonalObligation.expected_amount || 0).toLocaleString()}
              </div>
              <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                Round #{selectedPersonalObligation.period_number || selectedPersonalObligation.period_round || 1} • Due: {selectedPersonalObligation.due_date}
              </div>
            </div>

            {/* Payment Method Selector */}
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem', color: '#334155' }}>Choose Contribution Method</label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setPersonalPaymentMethod('DIGITAL')}
                  style={{
                    padding: '0.65rem 0.5rem',
                    borderRadius: '8px',
                    border: personalPaymentMethod === 'DIGITAL' ? '2px solid #2563eb' : '1px solid #e2e8f0',
                    background: personalPaymentMethod === 'DIGITAL' ? '#eff6ff' : '#fff',
                    color: personalPaymentMethod === 'DIGITAL' ? '#1d4ed8' : '#334155',
                    fontWeight: 600,
                    fontSize: '0.82rem',
                    cursor: 'pointer'
                  }}
                >
                  Chapa Gateway
                </button>
                <button
                  type="button"
                  onClick={() => setPersonalPaymentMethod('BANK_TRANSFER')}
                  style={{
                    padding: '0.65rem 0.5rem',
                    borderRadius: '8px',
                    border: personalPaymentMethod === 'BANK_TRANSFER' ? '2px solid #2563eb' : '1px solid #e2e8f0',
                    background: personalPaymentMethod === 'BANK_TRANSFER' ? '#eff6ff' : '#fff',
                    color: personalPaymentMethod === 'BANK_TRANSFER' ? '#1d4ed8' : '#334155',
                    fontWeight: 600,
                    fontSize: '0.82rem',
                    cursor: 'pointer'
                  }}
                >
                  Bank Transfer
                </button>
                <button
                  type="button"
                  onClick={() => setPersonalPaymentMethod('CASH')}
                  style={{
                    padding: '0.65rem 0.5rem',
                    borderRadius: '8px',
                    border: personalPaymentMethod === 'CASH' ? '2px solid #2563eb' : '1px solid #e2e8f0',
                    background: personalPaymentMethod === 'CASH' ? '#eff6ff' : '#fff',
                    color: personalPaymentMethod === 'CASH' ? '#1d4ed8' : '#334155',
                    fontWeight: 600,
                    fontSize: '0.82rem',
                    cursor: 'pointer'
                  }}
                >
                  Cash In-Hand
                </button>
              </div>
            </div>

            {/* Method A: Chapa Gateway */}
            {personalPaymentMethod === 'DIGITAL' && (
              <div style={{ fontSize: '0.85rem', color: '#166534', marginBottom: '1.25rem', background: '#f0fdf4', padding: '0.85rem', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
                <div style={{ fontWeight: 700, marginBottom: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <CheckCircle2 size={16} color="#16a34a" /> Official Chapa Payment Gateway
                </div>
                <div>Direct digital checkout via Chapa (Ethiopian debit cards, Telebirr, CBE Birr, Awash, and mobile money). You will be redirected to the secure Chapa payment portal. Group funds belong exclusively to your Equb group.</div>

                {selectedPersonalObligation.has_subaccount ? (
                  <div style={{ marginTop: '0.75rem', padding: '0.6rem 0.75rem', background: '#dcfce7', borderRadius: '6px', border: '1px solid #86efac', color: '#15803d' }}>
                    <div style={{ fontWeight: 700, fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                      🏦 Group Common Account Settlement Verified
                    </div>
                    <div style={{ fontSize: '0.78rem', marginTop: '0.25rem' }}>
                      Group Bank: <strong>{selectedPersonalObligation.bank_name || 'Commercial Bank of Ethiopia (CBE)'}</strong><br />
                      Account: <strong>{selectedPersonalObligation.bank_account_number}</strong> ({selectedPersonalObligation.bank_account_name || selectedPersonalObligation.group_name})
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#166534', marginTop: '0.35rem' }}>
                      ✓ 100% of contribution settles straight into this group's common account via Chapa Subaccount.
                    </div>
                  </div>
                ) : (
                  <div style={{ marginTop: '0.75rem', padding: '0.5rem 0.75rem', background: '#ffffff', borderRadius: '6px', border: '1px solid #e2e8f0', color: '#64748b', fontSize: '0.78rem' }}>
                    🛡️ Group funds belong exclusively to your Equb group and remain strictly isolated from platform SaaS rent.
                  </div>
                )}
              </div>
            )}

            {/* Method B: Bank Transfer */}
            {personalPaymentMethod === 'BANK_TRANSFER' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <div style={{ fontSize: '0.8rem', background: '#eff6ff', padding: '0.75rem', borderRadius: '8px', color: '#1e40af', border: '1px solid #bfdbfe' }}>
                  Transfer directly to Group Common Account:<br />
                  <strong>Bank:</strong> {selectedPersonalObligation.bank_name || 'Commercial Bank of Ethiopia (CBE)'}<br />
                  <strong>Account:</strong> {selectedPersonalObligation.bank_account_number || '100023456789'}<br />
                  <strong>Name:</strong> {selectedPersonalObligation.bank_account_name || selectedPersonalObligation.group_name}
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.25rem', color: '#334155' }}>Bank Transfer Reference Number *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. CBE-ET-987654"
                    value={personalTransferRef}
                    onChange={(e) => setPersonalTransferRef(e.target.value)}
                    style={{ width: '100%', border: '1px solid #cbd5e1', padding: '0.55rem', borderRadius: '6px', background: '#fff', fontSize: '0.9rem' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.25rem', color: '#334155' }}>Notes / Depositor Name</label>
                  <input
                    type="text"
                    placeholder="Optional notes"
                    value={personalTransferNotes}
                    onChange={(e) => setPersonalTransferNotes(e.target.value)}
                    style={{ width: '100%', border: '1px solid #cbd5e1', padding: '0.55rem', borderRadius: '6px', background: '#fff', fontSize: '0.9rem' }}
                  />
                </div>
              </div>
            )}

            {/* Method C: Cash In-Hand */}
            {personalPaymentMethod === 'CASH' && (
              <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: '1.25rem', background: '#fff7ed', padding: '0.85rem', borderRadius: '8px', border: '1px solid #fed7aa' }}>
                Please hand the exact cash amount of <strong>ETB {Number(selectedPersonalObligation.remaining_amount || selectedPersonalObligation.expected_amount || 0).toLocaleString()}</strong> directly to the Group Treasurer for this group. The treasurer will record the receipt in the Cash Receipts Register for dual-confirmation.
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="org-btn-secondary"
                onClick={() => setShowPersonalPaymentModal(false)}
                style={{ padding: '0.6rem 1.2rem', borderRadius: '8px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              {personalPaymentMethod !== 'CASH' && (
                <button
                  type="button"
                  className="org-btn-primary"
                  onClick={handleExecutePersonalPayment}
                  disabled={payingPersonalObligation}
                  style={{ padding: '0.6rem 1.2rem', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  {payingPersonalObligation && <RefreshCw size={16} className="org-spin" />}
                  <span>Confirm & Submit Payment</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL 13: Overdue Case Resolution Modal (Dropdown 2: A, B, C) */}
      {showResolveModal && selectedOverdueCase && (
        <div className="org-modal-overlay">
          <div className="org-modal" style={{ maxWidth: '640px' }}>
            <div className="org-modal-header">
              <div className="org-modal-title">
                Resolve Overdue Case – {selectedOverdueCase.member_name}
              </div>
              <button type="button" className="org-menu-btn" onClick={() => setShowResolveModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleResolveOverdueSubmit}>
              <div className="org-modal-body">
                {/* Overdue Context Summary */}
                <div style={{ background: '#fef2f2', padding: '0.85rem 1rem', borderRadius: '8px', border: '1px solid #fecaca', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 700, color: '#991b1b', fontSize: '0.88rem' }}>
                      Outstanding Overdue Balance:
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#b91c1c', marginTop: '0.2rem' }}>
                      Original Due: {selectedOverdueCase.original_deadline} ({selectedOverdueCase.days_overdue || 0} days past deadline)
                    </div>
                  </div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#dc2626' }}>
                    ETB {Number(selectedOverdueCase.amount_overdue || 0).toLocaleString()}
                  </div>
                </div>

                {/* DROPDOWN 2: Overdue Resolution Method */}
                <div className="org-form-group">
                  <label className="org-label">
                    Resolution Action * (Dropdown 2: Overdue Resolution)
                  </label>
                  <select
                    className="org-select"
                    value={resolutionChoice}
                    onChange={(e) => setResolutionChoice(e.target.value)}
                  >
                    <option value="CONTINUE_WAITING">Option A – Continue waiting</option>
                    <option value="PAYMENT_AGREEMENT">Option B – Formal payment agreement</option>
                    <option value="MEMBERSHIP_REVIEW">Option C – Membership review</option>
                  </select>
                </div>

                {/* OPTION A FIELDS: CONTINUE WAITING */}
                {resolutionChoice === 'CONTINUE_WAITING' && (
                  <div style={{ background: '#fffbeb', padding: '1rem', borderRadius: '8px', border: '1px solid #fde68a', marginBottom: '1rem' }}>
                    <div style={{ fontWeight: 700, color: '#92400e', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                      Option A – Continue Waiting (Member Stays Active, Lottery Postponed)
                    </div>
                    <div className="org-form-group" style={{ marginBottom: '0.75rem' }}>
                      <label className="org-label">Follow-Up Extension (Days) *</label>
                      <input
                        type="number"
                        className="org-input"
                        required
                        min="1"
                        max="30"
                        value={waitingDays}
                        onChange={(e) => setWaitingDays(e.target.value)}
                      />
                    </div>
                    <div className="org-form-group" style={{ marginBottom: '0.5rem' }}>
                      <label className="org-label">Documented Organizer Reason *</label>
                      <textarea
                        className="org-textarea"
                        rows="2"
                        required
                        value={waitingReason}
                        onChange={(e) => setWaitingReason(e.target.value)}
                        placeholder="e.g. Member contacted organizer; awaiting salary processing delay."
                      />
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#b45309' }}>
                      ℹ️ In accordance with group rules, the member stays active, notifications are sent to the member and Treasurer, and the lottery remains postponed until this follow-up deadline.
                    </div>
                  </div>
                )}

                {/* OPTION B FIELDS: FORMAL PAYMENT AGREEMENT */}
                {resolutionChoice === 'PAYMENT_AGREEMENT' && (
                  <div style={{ background: '#eff6ff', padding: '1rem', borderRadius: '8px', border: '1px solid #bfdbfe', marginBottom: '1rem' }}>
                    <div style={{ fontWeight: 700, color: '#1e40af', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                      Option B – Structured Payment Installment Agreement
                    </div>
                    <div className="org-form-group" style={{ marginBottom: '0.75rem' }}>
                      <label className="org-label">Reason / Hardship Justification *</label>
                      <input
                        type="text"
                        className="org-input"
                        required
                        value={agreementReason}
                        onChange={(e) => setAgreementReason(e.target.value)}
                        placeholder="e.g. Medical emergency repayment plan"
                      />
                    </div>

                    <div style={{ marginBottom: '0.75rem' }}>
                      <label className="org-label" style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span>Installment Repayment Schedule</span>
                        <button
                          type="button"
                          onClick={() => {
                            const newIdx = agreementInstallments.length + 1;
                            setAgreementInstallments([
                              ...agreementInstallments,
                              { amount: '1000', due_date: new Date(Date.now() + newIdx * 7 * 86400000).toISOString().split('T')[0] }
                            ]);
                          }}
                          style={{ border: 'none', background: 'none', color: '#2563eb', fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer' }}
                        >
                          + Add Installment
                        </button>
                      </label>

                      {agreementInstallments.map((inst, idx) => (
                        <div key={idx} style={{ display: 'grid', gridTemplateColumns: '80px 1fr 1fr auto', gap: '0.5rem', alignItems: 'center', marginBottom: '0.4rem' }}>
                          <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#334155' }}>#{idx + 1}</span>
                          <input
                            type="number"
                            className="org-input"
                            required
                            placeholder="Amount (ETB)"
                            value={inst.amount}
                            onChange={(e) => {
                              const updated = [...agreementInstallments];
                              updated[idx].amount = e.target.value;
                              setAgreementInstallments(updated);
                            }}
                          />
                          <input
                            type="date"
                            className="org-input"
                            required
                            value={inst.due_date}
                            onChange={(e) => {
                              const updated = [...agreementInstallments];
                              updated[idx].due_date = e.target.value;
                              setAgreementInstallments(updated);
                            }}
                          />
                          {agreementInstallments.length > 1 && (
                            <button
                              type="button"
                              onClick={() => {
                                setAgreementInstallments(agreementInstallments.filter((_, i) => i !== idx));
                              }}
                              style={{ border: 'none', background: 'none', color: '#ef4444', cursor: 'pointer' }}
                            >
                              <X size={16} />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>

                    <div style={{ fontSize: '0.75rem', color: '#1d4ed8' }}>
                      ℹ️ Generates an official payment agreement requiring digital member acceptance. Group Treasurer will monitor installment settlements.
                    </div>
                  </div>
                )}

                {/* OPTION C FIELDS: MEMBERSHIP REVIEW */}
                {resolutionChoice === 'MEMBERSHIP_REVIEW' && (
                  <div style={{ background: '#f5f3ff', padding: '1rem', borderRadius: '8px', border: '1px solid #ddd6fe', marginBottom: '1rem' }}>
                    <div style={{ fontWeight: 700, color: '#6d28d9', fontSize: '0.85rem', marginBottom: '0.5rem' }}>
                      Option C – Formal Documented Membership Review & Net Settlement Audit
                    </div>

                    {/* Financial Summary Audit */}
                    <div style={{ background: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0', marginBottom: '0.75rem', fontSize: '0.82rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <span style={{ color: '#64748b' }}>Outstanding Balance:</span>
                        <strong style={{ color: '#dc2626' }}>ETB {Number(selectedOverdueCase.amount_overdue || 0).toLocaleString()}</strong>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <span style={{ color: '#64748b' }}>Financial Audit:</span>
                        <span>Full account audit will determine net refund or obligation balance.</span>
                      </div>
                    </div>

                    <div className="org-form-group" style={{ marginBottom: '0.75rem' }}>
                      <label className="org-label">Review Justification *</label>
                      <textarea
                        className="org-textarea"
                        rows="2"
                        required
                        value={reviewReason}
                        onChange={(e) => setReviewReason(e.target.value)}
                        placeholder="Document the exact basis for membership review..."
                      />
                    </div>

                    <div className="org-form-group" style={{ marginBottom: '0.75rem' }}>
                      <label className="org-label">Review Decision *</label>
                      <select
                        className="org-select"
                        value={reviewDecision}
                        onChange={(e) => setReviewDecision(e.target.value)}
                      >
                        <option value="REPLACE_MEMBER">Replace Member with New Candidate</option>
                        <option value="REMOVE_MEMBER">Remove Member with Financial Settlement</option>
                        <option value="REINSTATE_MEMBER">Reinstate Active Membership</option>
                      </select>
                    </div>

                    {reviewDecision === 'REPLACE_MEMBER' && (
                      <div className="org-form-group" style={{ marginBottom: '0.5rem' }}>
                        <label className="org-label">Replacement Candidate</label>
                        <select
                          className="org-select"
                          value={replacementUserId}
                          onChange={(e) => setReplacementUserId(e.target.value)}
                        >
                          <option value="">-- Choose Replacement Member (or Leave for Open Invite) --</option>
                          {groupMembers
                            .filter(m => m.membership_id !== selectedOverdueCase.membership_id)
                            .map(m => (
                              <option key={m.membership_id} value={m.user_id || m.id}>
                                {m.full_name} ({m.email})
                              </option>
                            ))}
                        </select>
                        <div style={{ fontSize: '0.74rem', color: '#6d28d9', marginTop: '0.25rem' }}>
                          ⚠️ Replacement Rule: Replacement assumes future contribution obligations. In lottery draws, replacement takes their natural position in remaining rounds and never jumps ahead of established members.
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="org-modal-footer">
                <button
                  type="button"
                  className="org-btn-secondary"
                  onClick={() => setShowResolveModal(false)}
                  disabled={resolvingCase}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="org-btn-primary"
                  disabled={resolvingCase}
                  style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}
                >
                  {resolvingCase && <RefreshCw size={14} className="org-spin" />}
                  <span>Confirm Resolution</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
