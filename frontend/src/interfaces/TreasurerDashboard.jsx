import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { useTheme } from '../context/ThemeContext';
import { HeaderControls } from '../components/HeaderControls';
import { NotificationCenter } from '../components/NotificationCenter';
import { ToastNotification } from '../components/ToastNotification';
import { ChatWidget } from '../components/ChatWidget';
import { processAvatarImage } from '../utils/imageHelper';
import './TreasurerDashboard.css';

import {
  LayoutDashboard,
  Users,
  Wallet,
  CheckCircle2,
  Gift,
  FileBarChart,
  Bell,
  Settings,
  HelpCircle,
  Menu,
  X,
  Search,
  ChevronDown,
  LogOut,
  ArrowUpRight,
  ShieldCheck,
  AlertTriangle,
  Receipt,
  FileCheck,
  RefreshCw,
  Clock,
  Printer,
  Download,
  AlertCircle,
  Camera,
  Check,
  FileText
} from 'lucide-react';

export function TreasurerDashboard() {
  const { user, setUser, logout, setCurrentInterface, refreshUser } = useAuth();
  const { t, language, setLanguage, toggleLanguage } = useLanguage();
  const { effectiveTheme } = useTheme();

  // Navigation & UI state
  const [activeTab, setActiveTab] = useState('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);
  const profileRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(e) {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileMenuOpen(false);
      }
    }
    if (profileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [profileMenuOpen]);

  const [selectedGroupId, setSelectedGroupId] = useState('');
  const [dateFilter, setDateFilter] = useState('30');
  const [searchTerm, setSearchTerm] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  // Core Data States
  const [dashboardData, setDashboardData] = useState(null);
  const [overdueMonitoring, setOverdueMonitoring] = useState(null);
  const [assignedGroups, setAssignedGroups] = useState([]);
  const [contributionsData, setContributionsData] = useState(null);
  const [cashReceiptsList, setCashReceiptsList] = useState([]);
  const [reconciliationData, setReconciliationData] = useState(null);
  const [approvalsData, setApprovalsData] = useState(null);
  const [payoutsData, setPayoutsData] = useState(null);
  const [reportsData, setReportsData] = useState(null);
  const [settingsData, setSettingsData] = useState(null);
  const [notificationsList, setNotificationsList] = useState([]);

  // Loading & Feedback
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Modals state
  const [profileForm, setProfileForm] = useState({
    full_name: '',
    email: '',
    phone_number: '',
    preferred_language: 'en',
    avatar: '',
    current_password: '',
    new_password: '',
    confirm_new_password: '',
    change_password: false
  });
  const [profileSaving, setProfileSaving] = useState(false);

  useEffect(() => {
    if (user) {
      setProfileForm(prev => ({
        ...prev,
        full_name: user.full_name || '',
        email: user.email || '',
        phone_number: user.phone_number || '',
        preferred_language: user.preferred_language || 'en',
        avatar: user.avatar || ''
      }));
    }
  }, [user]);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    try {
      setProfileSaving(true);
      setErrorMessage('');

      if (profileForm.change_password) {
        if (!profileForm.new_password || profileForm.new_password.length < 8) {
          setErrorMessage('New password must be at least 8 characters long.');
          setProfileSaving(false);
          return;
        }
        if (profileForm.new_password !== profileForm.confirm_new_password) {
          setErrorMessage('New password confirmation does not match.');
          setProfileSaving(false);
          return;
        }
      }

      const payload = {
        full_name: profileForm.full_name.trim(),
        phone_number: profileForm.phone_number.trim(),
        avatar: profileForm.avatar,
        preferred_language: profileForm.preferred_language
      };
      if (profileForm.change_password && profileForm.new_password) {
        payload.current_password = profileForm.current_password;
        payload.new_password = profileForm.new_password;
      }

      const res = await api.updateProfile(payload);
      if (res?.user && setUser) {
        setUser(prev => ({ ...prev, ...res.user }));
      }
      if (refreshUser) refreshUser();
      setSuccessMessage('Treasurer profile and credentials updated successfully.');
      setProfileForm(prev => ({
        ...prev,
        current_password: '',
        new_password: '',
        confirm_new_password: '',
        change_password: false
      }));
      setTimeout(() => setSuccessMessage(''), 4000);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to update treasurer profile.');
    } finally {
      setProfileSaving(false);
    }
  };
  const [showRecordCashModal, setShowRecordCashModal] = useState(false);
  const [recordCashForm, setRecordCashForm] = useState({ obligation_id: '', amount: '', receipt_number: '', notes: '' });

  const [showPrintReceiptModal, setShowPrintReceiptModal] = useState(false);
  const [activePrintReceipt, setActivePrintReceipt] = useState(null);

  const [showReconcileModal, setShowReconcileModal] = useState(false);
  const [reconcileTarget, setReconcileTarget] = useState(null);
  const [reconcileNotes, setReconcileNotes] = useState('');

  const [showFlagExceptionModal, setShowFlagExceptionModal] = useState(false);
  const [flagExceptionForm, setFlagExceptionForm] = useState({ exception_type: 'DUPLICATE_REFERENCE', reference_number: '', expected_amount: '', actual_amount: '', description: '' });

  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [approvalTarget, setApprovalTarget] = useState(null);
  const [approvalDecision, setApprovalDecision] = useState('APPROVE');
  const [approvalReason, setApprovalReason] = useState('');

  const [showRequestPayoutModal, setShowRequestPayoutModal] = useState(false);
  const [requestPayoutForm, setRequestPayoutForm] = useState({ membership_id: '', amount: '', notes: '' });

  const [showExecutePayoutModal, setShowExecutePayoutModal] = useState(false);
  const [executePayoutTarget, setExecutePayoutTarget] = useState(null);
  const [executionRef, setExecutionRef] = useState('');
  const [executionNotes, setExecutionNotes] = useState('');

  const [showGroupDetailModal, setShowGroupDetailModal] = useState(false);
  const [selectedGroupDetail, setSelectedGroupDetail] = useState(null);

  // Personal Contribution Obligations state
  const [personalObligations, setPersonalObligations] = useState([]);
  const [showPersonalPaymentModal, setShowPersonalPaymentModal] = useState(false);
  const [selectedPersonalObligation, setSelectedPersonalObligation] = useState(null);
  const [personalPaymentMethod, setPersonalPaymentMethod] = useState('DIGITAL'); // 'DIGITAL' | 'BANK_TRANSFER' | 'CASH'
  const [personalTransferRef, setPersonalTransferRef] = useState('');
  const [personalTransferNotes, setPersonalTransferNotes] = useState('');
  const [payingPersonalObligation, setPayingPersonalObligation] = useState(false);

  // Load Personal Obligations
  const loadPersonalObligations = async () => {
    try {
      const res = await api.getMyObligations();
      setPersonalObligations(Array.isArray(res) ? res : (res?.results || []));
    } catch (err) {
      console.error('Failed to load treasurer personal obligations:', err);
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
      setErrorMessage('');
      if (personalPaymentMethod === 'DIGITAL') {
        const res = await api.payDigital(selectedPersonalObligation.id, 'CHAPA');
        if (res.checkout_url) {
          setSuccessMessage(`Chapa checkout session initiated! (Ref: ${res.tx_ref || res.internal_reference}). Redirecting to payment portal...`);
          setShowPersonalPaymentModal(false);
          window.location.href = res.checkout_url;
          return;
        } else {
          setSuccessMessage(`Chapa payment initiated successfully! Internal Ref: ${res.internal_reference || res.tx_ref}.`);
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
        setSuccessMessage(`Bank transfer ${personalTransferRef} submitted for reconciliation.`);
      }
      setShowPersonalPaymentModal(false);
      await loadPersonalObligations();
      const gid = selectedGroupId || assignedGroups[0]?.id;
      if (gid) {
        await loadTabData('contributions');
      }
      await loadDashboard();
    } catch (err) {
      setErrorMessage(err.message || 'Payment submission failed.');
    } finally {
      setPayingPersonalObligation(false);
    }
  };

  // Load Dashboard Data
  const loadDashboard = async () => {
    try {
      setLoading(true);
      setErrorMessage('');
      loadPersonalObligations();
      const data = await api.getTreasurerDashboard(selectedGroupId);
      setDashboardData(data);
      if (data.assigned_groups_options && data.assigned_groups_options.length > 0) {
        setAssignedGroups(data.assigned_groups_options);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to load dashboard.');
    } finally {
      setLoading(false);
    }
  };

  // Load Specific Tab Data
  const loadTabData = async (tab) => {
    try {
      setErrorMessage('');
      const gid = selectedGroupId || (assignedGroups[0]?.id || '');
      if (tab === 'my_groups') {
        const res = await api.getTreasurerGroups();
        setAssignedGroups(res);
      } else if (tab === 'contributions' && gid) {
        const res = await api.getTreasurerContributions(gid, { search: searchTerm });
        setContributionsData(res);
      } else if (tab === 'cash_receipts' && gid) {
        const res = await api.getTreasurerCashReceipts(gid);
        setCashReceiptsList(res);
      } else if (tab === 'reconciliation' && gid) {
        const res = await api.getTreasurerReconciliation(gid);
        setReconciliationData(res);
      } else if (tab === 'approvals') {
        const res = await api.getTreasurerApprovals();
        setApprovalsData(res);
      } else if (tab === 'payouts' && gid) {
        const res = await api.getTreasurerPayouts(gid);
        setPayoutsData(res);
      } else if (tab === 'reports' && gid) {
        const res = await api.getTreasurerReports(gid);
        setReportsData(res);
      } else if (tab === 'notifications') {
        const res = await api.getNotifications();
        const list = Array.isArray(res) ? res : (res?.results || []);
        setNotificationsList(list);
      } else if (tab === 'settings') {
        const res = await api.getTreasurerSettings();
        setSettingsData(res);
      } else if (tab === 'overdue_monitoring' && gid) {
        const res = await api.getTreasurerOverdueMonitoring(gid);
        setOverdueMonitoring(res);
      }
    } catch (err) {
      setErrorMessage(err.message || `Failed to load ${tab} data.`);
    }
  };

  const handleRefreshAll = async () => {
    try {
      setRefreshing(true);
      setErrorMessage('');
      const gid = selectedGroupId || (assignedGroups[0]?.id || '');
      await Promise.all([
        loadDashboard(),
        loadTabData(activeTab),
        gid ? api.getTreasurerOverdueMonitoring(gid).then(res => setOverdueMonitoring(res)).catch(() => {}) : Promise.resolve(),
        loadPersonalObligations()
      ]);
      setSuccessMessage('Financial records refreshed successfully!');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to refresh financial records.');
    } finally {
      setRefreshing(false);
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

    if (txRef && (txRef.startsWith('EQUB-') || txRef.includes('EQUB-'))) {
      const verifyReturn = async () => {
        try {
          setActionLoading(true);
          const verRes = await api.verifyChapaPayment(txRef);
          if (verRes.status === 'CONFIRMED' || verRes.success) {
            setSuccessMessage(`Personal group contribution payment confirmed via Chapa! Receipt #${verRes.receipt_number || txRef}. Group funds allocated.`);
          } else {
            setErrorMessage(`Chapa contribution status: ${verRes.status || 'Verification pending'}.`);
          }
        } catch (err) {
          setErrorMessage(err.message || 'Chapa contribution verification failed.');
        } finally {
          window.history.replaceState({}, document.title, window.location.pathname);
          await loadDashboard();
          await loadPersonalObligations();
          setActionLoading(false);
        }
      };
      verifyReturn();
    } else {
      loadDashboard();
      loadPersonalObligations();
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [selectedGroupId]);

  useEffect(() => {
    if (activeTab !== 'dashboard') {
      loadTabData(activeTab);
    }
  }, [activeTab, selectedGroupId]);

  // Modal Handlers
  const handleRecordCashSubmit = async (e) => {
    e.preventDefault();
    const gid = selectedGroupId || assignedGroups[0]?.id;
    if (!gid) return;
    try {
      setActionLoading(true);
      setErrorMessage('');
      const res = await api.treasurerRecordCash(gid, recordCashForm);
      setSuccessMessage(res.message || 'Cash receipt recorded successfully!');
      setShowRecordCashModal(false);
      setRecordCashForm({ obligation_id: '', amount: '', receipt_number: '', notes: '' });
      loadDashboard();
      if (activeTab === 'cash_receipts' || activeTab === 'contributions') {
        loadTabData(activeTab);
      }
    } catch (err) {
      setErrorMessage(err.message || 'Failed to record cash receipt.');
    } finally {
      setActionLoading(false);
    }
  };

  const handlePrintReceipt = async (receiptId) => {
    try {
      setActionLoading(true);
      const res = await api.getTreasurerCashReceiptDetail(receiptId);
      setActivePrintReceipt(res);
      setShowPrintReceiptModal(true);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to fetch receipt.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReconcileActionSubmit = async (decision) => {
    const gid = selectedGroupId || assignedGroups[0]?.id;
    if (!gid || !reconcileTarget) return;
    try {
      setActionLoading(true);
      setErrorMessage('');
      const res = await api.treasurerReconcileMatch(gid, {
        payment_id: reconcileTarget.id,
        decision: decision,
        notes: reconcileNotes
      });
      setSuccessMessage(res.message || 'Transfer reconciliation processed.');
      setShowReconcileModal(false);
      setReconcileTarget(null);
      setReconcileNotes('');
      loadDashboard();
      if (activeTab === 'reconciliation') loadTabData('reconciliation');
    } catch (err) {
      setErrorMessage(err.message || 'Reconciliation failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleFlagExceptionSubmit = async (e) => {
    e.preventDefault();
    const gid = selectedGroupId || assignedGroups[0]?.id;
    if (!gid) return;
    try {
      setActionLoading(true);
      setErrorMessage('');
      const res = await api.treasurerFlagException(gid, flagExceptionForm);
      setSuccessMessage(res.message || 'Exception flagged successfully.');
      setShowFlagExceptionModal(false);
      setFlagExceptionForm({ exception_type: 'DUPLICATE_REFERENCE', reference_number: '', expected_amount: '', actual_amount: '', description: '' });
      if (activeTab === 'reconciliation') loadTabData('reconciliation');
    } catch (err) {
      setErrorMessage(err.message || 'Failed to flag exception.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleApprovalActionSubmit = async () => {
    if (!approvalTarget) return;
    try {
      setActionLoading(true);
      setErrorMessage('');
      const type = approvalTarget.action_type === 'CASH_CONFIRMATION' ? 'cash' : 'payout';
      const res = await api.treasurerApprovalAction(type, approvalTarget.id, approvalDecision, approvalReason);
      setSuccessMessage(res.message || 'Approval decision recorded successfully.');
      setShowApprovalModal(false);
      setApprovalTarget(null);
      setApprovalReason('');
      loadDashboard();
      if (activeTab === 'approvals') loadTabData('approvals');
    } catch (err) {
      setErrorMessage(err.message || 'Approval action failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRequestPayoutSubmit = async (e) => {
    e.preventDefault();
    const gid = selectedGroupId || assignedGroups[0]?.id;
    if (!gid) return;
    try {
      setActionLoading(true);
      setErrorMessage('');
      const res = await api.treasurerRequestPayout(gid, requestPayoutForm);
      setSuccessMessage(res.message || 'Payout request created.');
      setShowRequestPayoutModal(false);
      setRequestPayoutForm({ membership_id: '', amount: '', notes: '' });
      loadDashboard();
      if (activeTab === 'payouts') loadTabData('payouts');
    } catch (err) {
      setErrorMessage(err.message || 'Failed to request payout.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleExecutePayoutSubmit = async (e) => {
    e.preventDefault();
    if (!executePayoutTarget) return;
    try {
      setActionLoading(true);
      setErrorMessage('');
      const res = await api.treasurerExecutePayout(executePayoutTarget.id, {
        execution_reference: executionRef,
        notes: executionNotes
      });
      setSuccessMessage(res.message || 'Payout disbursement executed and recorded in ledger.');
      setShowExecutePayoutModal(false);
      setExecutePayoutTarget(null);
      setExecutionRef('');
      setExecutionNotes('');
      loadDashboard();
      if (activeTab === 'payouts') loadTabData('payouts');
    } catch (err) {
      setErrorMessage(err.message || 'Payout execution failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleViewGroupDetails = async (groupId) => {
    try {
      setActionLoading(true);
      const res = await api.getTreasurerGroupDetail(groupId);
      setSelectedGroupDetail(res);
      setShowGroupDetailModal(true);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to fetch group details.');
    } finally {
      setActionLoading(false);
    }
  };

  // Quick Action Navigator
  const handleQuickAction = (actionKey) => {
    switch (actionKey) {
      case 'contributions':
        setActiveTab('contributions');
        break;
      case 'approvals':
        setActiveTab('approvals');
        break;
      case 'payouts':
        setActiveTab('payouts');
        break;
      case 'reports':
        setActiveTab('reports');
        break;
      case 'groups':
        setActiveTab('my_groups');
        break;
      case 'support':
        setActiveTab('help');
        break;
      default:
        break;
    }
  };

  return (
    <div className="tre-container" data-theme={effectiveTheme}>
      {/* Mobile Overlay */}
      <div
        className={`tre-sidebar-overlay ${sidebarOpen ? 'active' : ''}`}
        onClick={() => setSidebarOpen(false)}
      />

      {/* 1. Dark Navy Sidebar (Matching Mockup) */}
      <aside className={`tre-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="tre-logo-container">
          <div className="tre-logo-emblem">
            <ShieldCheck size={22} />
          </div>
          <div className="tre-brand-text">
            <span className="tre-brand-title">Digital Equb</span>
            <span className="tre-brand-sub">Ethiopia</span>
          </div>
        </div>

        <nav className="tre-nav-menu">
          <button
            className={`tre-nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => { setActiveTab('dashboard'); setSidebarOpen(false); }}
          >
            <LayoutDashboard size={18} />
            <span>Dashboard</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'my_groups' ? 'active' : ''}`}
            onClick={() => { setActiveTab('my_groups'); setSidebarOpen(false); }}
          >
            <Users size={18} />
            <span>My Group</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'contributions' ? 'active' : ''}`}
            onClick={() => { setActiveTab('contributions'); setSidebarOpen(false); }}
          >
            <Wallet size={18} />
            <span>Contributions</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'cash_receipts' ? 'active' : ''}`}
            onClick={() => { setActiveTab('cash_receipts'); setSidebarOpen(false); }}
          >
            <Receipt size={18} />
            <span>Cash Receipts</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'reconciliation' ? 'active' : ''}`}
            onClick={() => { setActiveTab('reconciliation'); setSidebarOpen(false); }}
          >
            <RefreshCw size={18} />
            <span>Reconciliation</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'approvals' ? 'active' : ''}`}
            onClick={() => { setActiveTab('approvals'); setSidebarOpen(false); }}
          >
            <CheckCircle2 size={18} />
            <span>Approvals</span>
            <span className="tre-nav-badge">{dashboardData?.kpis?.pending_approvals || 3}</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'overdue_monitoring' ? 'active' : ''}`}
            onClick={() => { setActiveTab('overdue_monitoring'); setSidebarOpen(false); }}
          >
            <AlertTriangle size={18} />
            <span>Overdue & Agreements</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'payouts' ? 'active' : ''}`}
            onClick={() => { setActiveTab('payouts'); setSidebarOpen(false); }}
          >
            <Gift size={18} />
            <span>Payouts</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'reports' ? 'active' : ''}`}
            onClick={() => { setActiveTab('reports'); setSidebarOpen(false); }}
          >
            <FileBarChart size={18} />
            <span>Reports</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'notifications' ? 'active' : ''}`}
            onClick={() => { setActiveTab('notifications'); setSidebarOpen(false); }}
          >
            <Bell size={18} />
            <span>Notifications</span>
            <span className="tre-nav-badge">3</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'settings' ? 'active' : ''}`}
            onClick={() => { setActiveTab('settings'); setSidebarOpen(false); }}
          >
            <Settings size={18} />
            <span>Settings</span>
          </button>

          <button
            className={`tre-nav-item ${activeTab === 'help' ? 'active' : ''}`}
            onClick={() => { setActiveTab('help'); setSidebarOpen(false); }}
          >
            <HelpCircle size={18} />
            <span>Help & Support</span>
          </button>
        </nav>

        {/* Sidebar Footer Badge */}
        <div className="tre-sidebar-footer">
          <div className="tre-panel-badge-card">
            <div className="tre-panel-icon">
              <Check size={18} />
            </div>
            <div className="tre-panel-text">
              <span className="tre-panel-title">Treasurer Panel</span>
              <span className="tre-panel-sub">Secure Access</span>
            </div>
          </div>
        </div>
      </aside>

      {/* 2. Main Workspace */}
      <div className="tre-main">
        {/* Top Navigation Bar */}
        <header className="tre-topbar">
          <div className="tre-topbar-left">
            <button
              className="tre-mobile-menu-btn"
              onClick={() => setSidebarOpen(true)}
              aria-label="Toggle navigation"
            >
              <Menu size={22} />
            </button>

            <button
              type="button"
              className="tre-refresh-btn"
              onClick={handleRefreshAll}
              disabled={refreshing}
              title="Refresh financial records"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.45rem 0.8rem',
                borderRadius: '8px',
                border: '1px solid var(--tre-border, #e2e8f0)',
                background: 'var(--tre-card-bg, #ffffff)',
                color: 'var(--tre-text-main, #0f172a)',
                cursor: 'pointer',
                fontSize: '0.82rem',
                fontWeight: 600
              }}
            >
              <RefreshCw size={15} className={refreshing ? 'tre-spin' : ''} />
              <span className="tre-refresh-text">{refreshing ? 'Syncing...' : 'Refresh'}</span>
            </button>

            <div className="tre-search-box">
              <Search className="tre-search-icon" size={16} />
              <input
                type="text"
                className="tre-search-input"
                placeholder={t('treSearchPlaceholder')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            {/* Optional Group Filter */}
            {assignedGroups.length > 1 && (
              <select
                className="tre-group-select"
                value={selectedGroupId}
                onChange={(e) => setSelectedGroupId(e.target.value)}
              >
                <option value="">All Assigned Groups</option>
                {assignedGroups.map((g) => (
                  <option key={g.id} value={g.id}>{g.name}</option>
                ))}
              </select>
            )}
          </div>

          <div className="tre-topbar-right">
            {/* Real Notification Center */}
            <NotificationCenter />

            {/* Theme & 4-Language Dropdowns */}
            <HeaderControls />

            {/* User Profile Dropdown */}
            <div
              className="tre-user-profile"
              ref={profileRef}
              onClick={() => setProfileMenuOpen(!profileMenuOpen)}
            >
              <div className="tre-user-avatar" style={{ overflow: 'hidden' }}>
                {user?.avatar ? (
                  <img src={user.avatar} alt="Avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  user?.full_name ? user.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : 'TR'
                )}
              </div>
              <div className="tre-user-info">
                <span className="tre-user-name">{user?.full_name || 'Treasurer'}</span>
                <span className="tre-user-role">{t('roleTreasurer') || 'Treasurer'} ▾</span>
              </div>

              {profileMenuOpen && (
                <div className="tre-profile-menu" onClick={(e) => e.stopPropagation()}>
                  <div style={{ padding: '0.4rem 0.75rem', borderBottom: '1px solid #f1f5f9', fontSize: '0.75rem', color: '#64748b' }}>
                    Signed in as <strong>{user?.email || 'Treasurer'}</strong>
                  </div>
                  <button
                    className="tre-menu-item"
                    onClick={() => { setActiveTab('settings'); setProfileMenuOpen(false); }}
                  >
                    <Settings size={16} />
                    <span>{t('navSettings')}</span>
                  </button>
                  <button
                    className="tre-menu-item danger"
                    onClick={() => { logout(); setProfileMenuOpen(false); }}
                  >
                    <LogOut size={16} />
                    <span>{t('logout') || 'Sign Out'}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Animated Movable Toast Notifications */}
        {errorMessage && (
          <ToastNotification
            message={errorMessage}
            type="error"
            onClose={() => setErrorMessage('')}
          />
        )}
        {successMessage && (
          <ToastNotification
            message={successMessage}
            type="success"
            onClose={() => setSuccessMessage('')}
          />
        )}

        {/* Content View Routing */}
        <main className="tre-content">
          {activeTab === 'dashboard' && (
            <>
              {/* Hero Welcome Banner */}
              <div className="tre-hero-banner">
                <div>
                  <h1 className="tre-hero-title">
                    Welcome back, {dashboardData?.treasurer_name?.split(' ')[0] || 'Abebe'}!
                  </h1>
                  <p className="tre-hero-sub">
                    Manage contributions and financial activities for your groups.
                  </p>
                </div>
                <select
                  className="tre-hero-date-select"
                  value={dateFilter}
                  onChange={(e) => setDateFilter(e.target.value)}
                >
                  <option value="30">Last 30 Days</option>
                  <option value="60">Last 60 Days</option>
                  <option value="90">Last 90 Days</option>
                </select>
              </div>

              {/* 4 Top KPI Cards */}
              <div className="tre-kpi-grid">
                {/* 1. My Groups */}
                <div className="tre-kpi-card">
                  <div className="tre-kpi-icon-box blue">
                    <Users size={24} />
                  </div>
                  <div className="tre-kpi-details">
                    <span className="tre-kpi-label">My Groups</span>
                    <span className="tre-kpi-value">{dashboardData?.kpis?.assigned_groups || 2}</span>
                    <span className="tre-kpi-sub green">Active: {dashboardData?.kpis?.active_groups || 2}</span>
                  </div>
                </div>

                {/* 2. Total Contributions */}
                <div className="tre-kpi-card">
                  <div className="tre-kpi-icon-box green">
                    <Wallet size={24} />
                  </div>
                  <div className="tre-kpi-details">
                    <span className="tre-kpi-label">Total Contributions</span>
                    <span className="tre-kpi-value">
                      ETB {Number(dashboardData?.kpis?.total_contributions_etb || 185000).toLocaleString()}
                    </span>
                    <span className="tre-kpi-sub green">↑ {dashboardData?.kpis?.contributions_growth_pct || 12}%</span>
                  </div>
                </div>

                {/* 3. Pending Approvals */}
                <div className="tre-kpi-card">
                  <div className="tre-kpi-icon-box purple">
                    <CheckCircle2 size={24} />
                  </div>
                  <div className="tre-kpi-details">
                    <span className="tre-kpi-label">Pending Approvals</span>
                    <span className="tre-kpi-value">{dashboardData?.kpis?.pending_approvals || 3}</span>
                    <span className="tre-kpi-sub purple">Requires Review</span>
                  </div>
                </div>

                {/* 4. Upcoming Payouts */}
                <div className="tre-kpi-card">
                  <div className="tre-kpi-icon-box orange">
                    <Gift size={24} />
                  </div>
                  <div className="tre-kpi-details">
                    <span className="tre-kpi-label">Upcoming Payouts</span>
                    <span className="tre-kpi-value">{dashboardData?.kpis?.upcoming_payouts || 1}</span>
                    <span className="tre-kpi-sub orange">Next: {dashboardData?.kpis?.next_payout_date || 'Jun 30, 2025'}</span>
                  </div>
                </div>
              </div>

              {/* Two Column Layout Matching Mockup */}
              <div className="tre-dashboard-grid">
                {/* Left Column: Line Chart + Recent Transactions */}
                <div className="tre-column">
                  {/* Group Financial Overview Line Chart */}
                  <div className="tre-card">
                    <div className="tre-card-header">
                      <div className="tre-card-title-group">
                        <FileBarChart size={18} color="#2563eb" />
                        <h2 className="tre-card-title">Group Financial Overview</h2>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div className="tre-chart-legend">
                          <span><span className="tre-legend-dot blue"></span>Expected</span>
                          <span><span className="tre-legend-dot green"></span>Received</span>
                        </div>
                        <select className="tre-hero-date-select" style={{ padding: '0.3rem 0.6rem', fontSize: '0.78rem' }}>
                          <option>Last 30 Days</option>
                        </select>
                      </div>
                    </div>

                    {/* SVG Line Chart */}
                    <div className="tre-svg-chart-container">
                      <svg viewBox="0 0 540 180" style={{ width: '100%', height: '100%' }}>
                        <defs>
                          <linearGradient id="blueLineGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#2563eb" stopOpacity="0.25" />
                            <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
                          </linearGradient>
                          <linearGradient id="greenLineGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#10b981" stopOpacity="0.2" />
                            <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
                          </linearGradient>
                        </defs>

                        {/* Grid lines */}
                        <line x1="40" y1="30" x2="520" y2="30" stroke="#f1f5f9" strokeWidth="1" />
                        <line x1="40" y1="65" x2="520" y2="65" stroke="#f1f5f9" strokeWidth="1" />
                        <line x1="40" y1="100" x2="520" y2="100" stroke="#f1f5f9" strokeWidth="1" />
                        <line x1="40" y1="135" x2="520" y2="135" stroke="#f1f5f9" strokeWidth="1" />
                        <line x1="40" y1="160" x2="520" y2="160" stroke="#e2e8f0" strokeWidth="1" />

                        {/* Y Axis Labels */}
                        <text x="10" y="34" fill="#94a3b8" fontSize="10">100K</text>
                        <text x="15" y="69" fill="#94a3b8" fontSize="10">75K</text>
                        <text x="15" y="104" fill="#94a3b8" fontSize="10">50K</text>
                        <text x="15" y="139" fill="#94a3b8" fontSize="10">25K</text>
                        <text x="25" y="164" fill="#94a3b8" fontSize="10">0K</text>

                        {/* X Axis Labels */}
                        <text x="50" y="176" fill="#94a3b8" fontSize="10">Jun 1</text>
                        <text x="160" y="176" fill="#94a3b8" fontSize="10">Jun 8</text>
                        <text x="270" y="176" fill="#94a3b8" fontSize="10">Jun 15</text>
                        <text x="380" y="176" fill="#94a3b8" fontSize="10">Jun 22</text>
                        <text x="480" y="176" fill="#94a3b8" fontSize="10">Jun 30</text>

                        {/* Area Fills */}
                        <polygon
                          points="60,130 170,95 285,75 395,55 495,45 495,160 60,160"
                          fill="url(#blueLineGrad)"
                        />
                        <polygon
                          points="60,145 170,118 285,98 395,78 495,68 495,160 60,160"
                          fill="url(#greenLineGrad)"
                        />

                        {/* Expected Blue Line */}
                        <polyline
                          fill="none"
                          stroke="#2563eb"
                          strokeWidth="2.5"
                          points="60,130 170,95 285,75 395,55 495,45"
                        />
                        <circle cx="60" cy="130" r="4" fill="#2563eb" stroke="#fff" strokeWidth="2" />
                        <circle cx="170" cy="95" r="4" fill="#2563eb" stroke="#fff" strokeWidth="2" />
                        <circle cx="285" cy="75" r="4" fill="#2563eb" stroke="#fff" strokeWidth="2" />
                        <circle cx="395" cy="55" r="4" fill="#2563eb" stroke="#fff" strokeWidth="2" />
                        <circle cx="495" cy="45" r="4" fill="#2563eb" stroke="#fff" strokeWidth="2" />

                        {/* Received Green Line */}
                        <polyline
                          fill="none"
                          stroke="#10b981"
                          strokeWidth="2.5"
                          points="60,145 170,118 285,98 395,78 495,68"
                        />
                        <circle cx="60" cy="145" r="4" fill="#10b981" stroke="#fff" strokeWidth="2" />
                        <circle cx="170" cy="118" r="4" fill="#10b981" stroke="#fff" strokeWidth="2" />
                        <circle cx="285" cy="98" r="4" fill="#10b981" stroke="#fff" strokeWidth="2" />
                        <circle cx="395" cy="78" r="4" fill="#10b981" stroke="#fff" strokeWidth="2" />
                        <circle cx="495" cy="68" r="4" fill="#10b981" stroke="#fff" strokeWidth="2" />
                      </svg>
                    </div>
                  </div>

                  {/* Recent Transactions Table */}
                  <div className="tre-card">
                    <div className="tre-card-header">
                      <div className="tre-card-title-group">
                        <Wallet size={18} color="#2563eb" />
                        <h2 className="tre-card-title">Recent Transactions</h2>
                      </div>
                      <span className="tre-view-all-link" onClick={() => setActiveTab('contributions')}>
                        View All →
                      </span>
                    </div>

                    <div className="tre-table-container">
                      <table className="tre-table">
                        <thead>
                          <tr>
                            <th>Date</th>
                            <th>Member</th>
                            <th>Amount</th>
                            <th>Status</th>
                            <th>Reference</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dashboardData?.recent_transactions?.map((tx, idx) => (
                            <tr key={tx.id || idx}>
                              <td>{tx.date}</td>
                              <td style={{ fontWeight: 600 }}>{tx.member_name}</td>
                              <td style={{ fontWeight: 700 }}>ETB {Number(tx.amount).toLocaleString()}</td>
                              <td>
                                <span className={`tre-status-badge ${tx.status?.toLowerCase() === 'confirmed' ? 'confirmed' : 'pending'}`}>
                                  {tx.status?.toLowerCase() === 'confirmed' ? <Check size={12} /> : <Clock size={12} />}
                                  {tx.status}
                                </span>
                              </td>
                              <td style={{ fontFamily: 'monospace', color: '#64748b' }}>{tx.reference}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                {/* Right Column: Your Groups + Quick Actions */}
                <div className="tre-column">
                  {/* Your Groups Card */}
                  <div className="tre-card">
                    <div className="tre-card-header">
                      <div className="tre-card-title-group">
                        <Users size={18} color="#2563eb" />
                        <h2 className="tre-card-title">Your Groups</h2>
                      </div>
                      <span className="tre-view-all-link" onClick={() => setActiveTab('my_groups')}>
                        View All →
                      </span>
                    </div>

                    {dashboardData?.your_groups?.map((g, idx) => (
                      <div key={g.id || idx} className="tre-group-item-card">
                        <div className={`tre-group-thumb ${idx % 2 === 1 ? 'secondary' : ''}`}>
                          <Users size={22} />
                        </div>
                        <div className="tre-group-info">
                          <div className="tre-group-header-row">
                            <span className="tre-group-name">{g.name}</span>
                            <span className="tre-badge-active">Active</span>
                          </div>
                          <div className="tre-group-meta">
                            {g.members_count} members • ETB {Number(g.contribution_amount).toLocaleString()}/month
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div className="tre-progress-bar-bg" style={{ flex: 1 }}>
                              <div
                                className="tre-progress-bar-fill"
                                style={{ width: `${g.progress_percentage || 70}%` }}
                              />
                            </div>
                            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b' }}>
                              {g.progress_percentage || 70}%
                            </span>
                          </div>
                        </div>
                        <button
                          className="tre-btn-view-group"
                          onClick={() => handleViewGroupDetails(g.id)}
                        >
                          View
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Quick Actions Card */}
                  <div className="tre-card">
                    <div className="tre-card-header" style={{ marginBottom: '0.75rem' }}>
                      <div className="tre-card-title-group">
                        <span style={{ fontSize: '1.1rem' }}>⚡</span>
                        <h2 className="tre-card-title">Quick Actions</h2>
                      </div>
                    </div>

                    <div className="tre-quick-actions-grid">
                      <div className="tre-action-tile" onClick={() => handleQuickAction('contributions')}>
                        <Wallet className="tre-action-icon" size={20} />
                        <span className="tre-action-label">View Contributions</span>
                      </div>

                      <div className="tre-action-tile" onClick={() => handleQuickAction('approvals')}>
                        <Users className="tre-action-icon" size={20} />
                        <span className="tre-action-label">Approve Members</span>
                      </div>

                      <div className="tre-action-tile" onClick={() => handleQuickAction('payouts')}>
                        <Gift className="tre-action-icon" size={20} />
                        <span className="tre-action-label">Manage Payouts</span>
                      </div>

                      <div className="tre-action-tile" onClick={() => handleQuickAction('reports')}>
                        <FileBarChart className="tre-action-icon" size={20} />
                        <span className="tre-action-label">View Reports</span>
                      </div>

                      <div className="tre-action-tile" onClick={() => handleQuickAction('groups')}>
                        <Settings className="tre-action-icon" size={20} />
                        <span className="tre-action-label">Manage Group</span>
                      </div>

                      <div className="tre-action-tile" onClick={() => handleQuickAction('support')}>
                        <HelpCircle className="tre-action-icon" size={20} />
                        <span className="tre-action-label">Contact Support</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* Tab 2: My Groups Full Management */}
          {activeTab === 'my_groups' && (
            <div className="tre-card">
              <div className="tre-card-header">
                <div>
                  <h2 className="tre-card-title">Assigned Equb Groups</h2>
                  <p className="tre-hero-sub">Groups where you hold active financial and treasurer authority.</p>
                </div>
              </div>

              <div className="tre-table-container">
                <table className="tre-table">
                  <thead>
                    <tr>
                      <th>Group Name</th>
                      <th>Organizer</th>
                      <th>Members</th>
                      <th>Monthly Fee</th>
                      <th>Confirmed Balance</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assignedGroups.map((g) => (
                      <tr key={g.id}>
                        <td style={{ fontWeight: 700 }}>{g.name}</td>
                        <td>{g.organizer_name || 'Selam Tesfaye'}</td>
                        <td>{g.members_count || 10}</td>
                        <td>ETB {Number(g.contribution_amount || 5000).toLocaleString()}</td>
                        <td style={{ color: '#10b981', fontWeight: 700 }}>
                          ETB {Number(g.available_funds_etb || 0).toLocaleString()}
                        </td>
                        <td><span className="tre-status-badge confirmed">ACTIVE</span></td>
                        <td>
                          <button
                            className="tre-btn-primary"
                            style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem' }}
                            onClick={() => handleViewGroupDetails(g.id)}
                          >
                            Financial Details
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 3: Contributions Monitoring */}
          {activeTab === 'contributions' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* SECTION A: Treasurer's Own Personal Contribution Obligation */}
              {(() => {
                const gid = selectedGroupId || assignedGroups[0]?.id;
                const myObligation = personalObligations.find((o) => o.group_id === gid) || personalObligations[0];
                if (!myObligation) return null;
                return (
                  <div className="tre-card" style={{ border: '1.5px solid #bfdbfe', background: '#f8fafc' }}>
                    <div className="tre-card-header" style={{ marginBottom: '0.75rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <Wallet size={20} color="#2563eb" />
                          <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800, color: '#1e3a8a' }}>
                            My Personal Contribution Obligation
                          </h3>
                          <span style={{ fontSize: '0.72rem', background: '#dbeafe', color: '#1e40af', padding: '0.15rem 0.45rem', borderRadius: '4px', fontWeight: 700 }}>
                            You (Treasurer Member)
                          </span>
                        </div>
                        <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.82rem', color: '#64748b' }}>
                          Your scheduled group savings obligation for <strong>{myObligation.group_name || 'your group'}</strong>.
                        </p>
                      </div>
                      {myObligation.status !== 'PAID' ? (
                        <button
                          type="button"
                          className="tre-btn-primary"
                          onClick={() => handleInitiatePersonalPayment(myObligation)}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', background: '#2563eb' }}
                        >
                          <Wallet size={15} />
                          <span>Pay My Contribution</span>
                        </button>
                      ) : (
                        <span style={{ color: '#10b981', fontWeight: 700, fontSize: '0.85rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                          <CheckCircle2 size={16} /> Obligation Fully Paid
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', padding: '1rem', background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 700 }}>PERIOD / ROUND</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a', marginTop: '0.2rem' }}>
                          Round #{myObligation.period_number || 1}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 700 }}>DUE DATE</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a', marginTop: '0.2rem' }}>
                          {myObligation.due_date || '-'}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 700 }}>EXPECTED AMOUNT</div>
                        <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#0f172a', marginTop: '0.2rem' }}>
                          ETB {Number(myObligation.expected_amount || 0).toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 700 }}>AMOUNT PAID</div>
                        <div style={{ fontSize: '1.15rem', fontWeight: 800, color: '#10b981', marginTop: '0.2rem' }}>
                          ETB {Number(myObligation.amount_paid || 0).toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 700 }}>STATUS</div>
                        <div style={{ marginTop: '0.25rem' }}>
                          <span className={`tre-status-badge ${myObligation.status === 'PAID' ? 'confirmed' : 'pending'}`}>
                            {myObligation.status_display || myObligation.status}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}

              {/* SECTION B: All Member Contribution Obligations Table */}
              <div className="tre-card">
                <div className="tre-card-header">
                  <div>
                    <h2 className="tre-card-title">Member Contribution Obligations</h2>
                    <p className="tre-hero-sub">Scheduled member contributions, payments, and outstanding balances.</p>
                  </div>
                  <button
                    className="tre-btn-primary"
                    onClick={() => setShowRecordCashModal(true)}
                  >
                    + Record Cash Receipt
                  </button>
                </div>

                <div className="tre-table-container">
                  <table className="tre-table">
                    <thead>
                      <tr>
                        <th>Member</th>
                        <th>Round</th>
                        <th>Due Date</th>
                        <th>Expected</th>
                        <th>Paid</th>
                        <th>Remaining</th>
                        <th>Status</th>
                        <th>Action</th>
                        <th>Last Ref</th>
                      </tr>
                    </thead>
                    <tbody>
                      {contributionsData?.obligations?.map((ob) => {
                        const isCurrentUser = ob.is_me || ob.member_email === user?.email || (user?.id && String(ob.member_user_id) === String(user.id));
                        return (
                          <tr key={ob.id} className={isCurrentUser ? 'tre-current-user-row' : ''}>
                            <td style={{ fontWeight: 600 }}>
                              {ob.member_name}
                              {isCurrentUser && (
                                <span style={{ fontSize: '0.7rem', background: '#2563eb', color: '#fff', padding: '0.1rem 0.4rem', borderRadius: '4px', marginLeft: '0.5rem' }}>
                                  You (Treasurer)
                                </span>
                              )}
                            </td>
                            <td>Round {ob.period_round}</td>
                            <td>{ob.due_date}</td>
                            <td>ETB {ob.expected_amount?.toLocaleString()}</td>
                            <td style={{ color: '#10b981', fontWeight: 700 }}>ETB {ob.confirmed_amount?.toLocaleString()}</td>
                            <td style={{ color: ob.outstanding_amount > 0 ? '#ef4444' : '#64748b', fontWeight: 600 }}>
                              ETB {ob.outstanding_amount?.toLocaleString()}
                            </td>
                            <td>
                              <span className={`tre-status-badge ${ob.status === 'PAID' ? 'confirmed' : 'pending'}`}>
                                {ob.status}
                              </span>
                            </td>
                            <td>
                              {isCurrentUser && ob.status !== 'PAID' ? (
                                <button
                                  type="button"
                                  className="tre-btn-primary"
                                  style={{ padding: '0.25rem 0.6rem', fontSize: '0.75rem', background: '#2563eb', display: 'inline-flex', alignItems: 'center', gap: '0.25rem' }}
                                  onClick={() => {
                                    const match = personalObligations.find((p) => p.id === ob.id) || {
                                      ...ob,
                                      group_name: assignedGroups[0]?.name,
                                      period_number: ob.period_round,
                                      remaining_amount: ob.outstanding_amount,
                                      expected_amount: ob.expected_amount
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
                            <td style={{ fontFamily: 'monospace', fontSize: '0.78rem' }}>{ob.last_payment_reference || '-'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Tab 4: Cash Receipts */}
          {activeTab === 'cash_receipts' && (
            <div className="tre-card">
              <div className="tre-card-header">
                <div>
                  <h2 className="tre-card-title">Cash Receipts Register</h2>
                  <p className="tre-hero-sub">In-person cash collections subject to dual-custody verification.</p>
                </div>
                <button className="tre-btn-primary" onClick={() => setShowRecordCashModal(true)}>
                  + Record Cash Receipt
                </button>
              </div>

              <div className="tre-table-container">
                <table className="tre-table">
                  <thead>
                    <tr>
                      <th>Receipt #</th>
                      <th>Member</th>
                      <th>Amount</th>
                      <th>Received By</th>
                      <th>Confirmed By</th>
                      <th>Status</th>
                      <th>Date</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cashReceiptsList.map((rcp) => (
                      <tr key={rcp.id}>
                        <td style={{ fontWeight: 700, fontFamily: 'monospace' }}>{rcp.receipt_number}</td>
                        <td>{rcp.member_name}</td>
                        <td style={{ fontWeight: 700 }}>ETB {rcp.amount?.toLocaleString()}</td>
                        <td>{rcp.received_by || 'Treasurer'}</td>
                        <td>{rcp.confirmed_by || '-'}</td>
                        <td>
                          <span className={`tre-status-badge ${rcp.status === 'CONFIRMED' ? 'confirmed' : 'pending'}`}>
                            {rcp.status}
                          </span>
                        </td>
                        <td>{rcp.received_at}</td>
                        <td>
                          <button
                            className="tre-btn-secondary"
                            style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                            onClick={() => handlePrintReceipt(rcp.id)}
                          >
                            <Printer size={14} style={{ marginRight: '0.25rem' }} /> Receipt
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 5: Payment Reconciliation Workspace */}
          {activeTab === 'reconciliation' && (
            <div className="tre-column">
              {/* Unmatched Bank Transfers */}
              <div className="tre-card">
                <div className="tre-card-header">
                  <div>
                    <h2 className="tre-card-title">Unmatched Bank & Mobile Money Transfers</h2>
                    <p className="tre-hero-sub">Reconcile member-submitted bank transfer slips with actual account deposits.</p>
                  </div>
                  <button
                    className="tre-btn-secondary"
                    onClick={() => setShowFlagExceptionModal(true)}
                  >
                    🚩 Flag Exception
                  </button>
                </div>

                <div className="tre-table-container">
                  <table className="tre-table">
                    <thead>
                      <tr>
                        <th>Transfer Ref</th>
                        <th>Member</th>
                        <th>Amount</th>
                        <th>Submitted At</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reconciliationData?.unmatched_transfers?.length === 0 ? (
                        <tr><td colSpan="5" style={{ textAlign: 'center', color: '#94a3b8', padding: '2rem' }}>No unmatched transfers pending review.</td></tr>
                      ) : (
                        reconciliationData?.unmatched_transfers?.map((tr) => (
                          <tr key={tr.id}>
                            <td style={{ fontWeight: 700, fontFamily: 'monospace' }}>{tr.transfer_reference}</td>
                            <td>{tr.member_name}</td>
                            <td style={{ fontWeight: 700 }}>ETB {tr.amount?.toLocaleString()}</td>
                            <td>{tr.submitted_at}</td>
                            <td style={{ display: 'flex', gap: '0.5rem' }}>
                              <button
                                className="tre-btn-primary"
                                style={{ padding: '0.3rem 0.6rem', fontSize: '0.78rem' }}
                                onClick={() => { setReconcileTarget(tr); setShowReconcileModal(true); }}
                              >
                                Reconcile
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Flagged Exceptions */}
              <div className="tre-card">
                <div className="tre-card-header">
                  <h2 className="tre-card-title">Flagged Discrepancies & Exceptions</h2>
                </div>
                <div className="tre-table-container">
                  <table className="tre-table">
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Reference</th>
                        <th>Expected</th>
                        <th>Actual</th>
                        <th>Description</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reconciliationData?.exceptions?.map((exc) => (
                        <tr key={exc.id}>
                          <td style={{ fontWeight: 600 }}>{exc.exception_type}</td>
                          <td style={{ fontFamily: 'monospace' }}>{exc.reference_number}</td>
                          <td>{exc.expected_amount ? `ETB ${exc.expected_amount}` : '-'}</td>
                          <td>{exc.actual_amount ? `ETB ${exc.actual_amount}` : '-'}</td>
                          <td>{exc.description}</td>
                          <td><span className="tre-status-badge pending">{exc.status}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Tab 6: Approvals Workspace */}
          {activeTab === 'approvals' && (
            <div className="tre-card">
              <div className="tre-card-header">
                <div>
                  <h2 className="tre-card-title">Pending Independent Approvals</h2>
                  <p className="tre-hero-sub">Actions requiring independent sign-off. Separation of duties is strictly enforced.</p>
                </div>
              </div>

              <div className="tre-table-container">
                <table className="tre-table">
                  <thead>
                    <tr>
                      <th>Action Type</th>
                      <th>Group</th>
                      <th>Initiator</th>
                      <th>Recipient / Payer</th>
                      <th>Amount</th>
                      <th>Reference</th>
                      <th>Date</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {approvalsData?.approvals?.map((app) => (
                      <tr key={app.id}>
                        <td style={{ fontWeight: 600 }}>{app.action_title}</td>
                        <td>{app.group_name}</td>
                        <td>{app.initiator_name}</td>
                        <td>{app.payer_name}</td>
                        <td style={{ fontWeight: 700 }}>ETB {app.amount?.toLocaleString()}</td>
                        <td style={{ fontFamily: 'monospace' }}>{app.reference}</td>
                        <td>{app.submission_date}</td>
                        <td>
                          {app.can_approve ? (
                            <button
                              className="tre-btn-primary"
                              style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem' }}
                              onClick={() => { setApprovalTarget(app); setShowApprovalModal(true); }}
                            >
                              Review & Sign
                            </button>
                          ) : (
                            <span style={{ fontSize: '0.72rem', color: '#ef4444', fontWeight: 600 }}>
                              🚫 Self-action blocked
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab: Overdue Contributions & Payment Agreements Monitoring */}
          {activeTab === 'overdue_monitoring' && (
            <div>
              <div className="tre-card" style={{ marginBottom: '1.25rem' }}>
                <div className="tre-card-header">
                  <div>
                    <h2 className="tre-card-title">Overdue Contributions & Payment Agreements</h2>
                    <p className="tre-hero-sub">
                      Monitor structured installment repayments, member compliance, and bank/cash dual-verification.
                    </p>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <button
                      type="button"
                      className="tre-btn-secondary"
                      onClick={() => {
                        const gid = selectedGroupId || assignedGroups[0]?.id;
                        if (gid) loadTabData('overdue_monitoring');
                      }}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}
                    >
                      <RefreshCw size={14} className={refreshing ? 'tre-spin' : ''} />
                      <span>Sync Agreements</span>
                    </button>
                  </div>
                </div>

                {/* Overdue Monitoring Stats */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--tre-border, #e2e8f0)' }}>
                  <div style={{ background: 'var(--tre-bg-muted, #f8fafc)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--tre-border, #e2e8f0)' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b' }}>Active Payment Agreements</div>
                    <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#2563eb', marginTop: '0.2rem' }}>
                      {(overdueMonitoring?.agreements || []).length}
                    </div>
                  </div>
                  <div style={{ background: 'var(--tre-bg-muted, #f8fafc)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--tre-border, #e2e8f0)' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b' }}>Total Overdue Cases</div>
                    <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#dc2626', marginTop: '0.2rem' }}>
                      {(overdueMonitoring?.overdue_cases || []).length}
                    </div>
                  </div>
                  <div style={{ background: 'var(--tre-bg-muted, #f8fafc)', padding: '0.85rem', borderRadius: '8px', border: '1px solid var(--tre-border, #e2e8f0)' }}>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b' }}>Pending Member Acceptances</div>
                    <div style={{ fontSize: '1.35rem', fontWeight: 800, color: '#d97706', marginTop: '0.2rem' }}>
                      {(overdueMonitoring?.agreements || []).filter(a => a.status === 'PENDING_MEMBER_ACCEPTANCE').length}
                    </div>
                  </div>
                </div>
              </div>

              {/* Active Payment Agreements & Installments Table */}
              <div className="tre-card" style={{ marginBottom: '1.25rem' }}>
                <div className="tre-card-header">
                  <div>
                    <h3 className="tre-card-title">Structured Repayment Agreements (Option B)</h3>
                    <p className="tre-hero-sub">
                      Payment schedules approved by the Organizer. Members make scheduled payments via Chapa, bank transfer, or cash.
                    </p>
                  </div>
                </div>

                <div className="tre-table-responsive">
                  <table className="tre-table">
                    <thead>
                      <tr>
                        <th>Member Name</th>
                        <th>Total Balance</th>
                        <th>Remaining</th>
                        <th>Agreement Status</th>
                        <th>Installments Breakdown</th>
                        <th>Reason / Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(overdueMonitoring?.agreements || []).map((agr) => (
                        <tr key={agr.id}>
                          <td style={{ fontWeight: 700 }}>
                            <div>{agr.member_name}</div>
                            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>{agr.member_email}</div>
                          </td>
                          <td style={{ fontWeight: 800 }}>
                            ETB {Number(agr.total_outstanding_amount || 0).toLocaleString()}
                          </td>
                          <td style={{ fontWeight: 800, color: '#dc2626' }}>
                            ETB {Number(agr.remaining_balance || 0).toLocaleString()}
                          </td>
                          <td>
                            <span className={`tre-badge ${agr.status === 'ACCEPTED' ? 'tre-badge-green' : (agr.status === 'PENDING_MEMBER_ACCEPTANCE' ? 'tre-badge-orange' : 'tre-badge-red')}`}>
                              {agr.status}
                            </span>
                          </td>
                          <td style={{ minWidth: '220px' }}>
                            {(agr.installments || []).map((inst, i) => (
                              <div
                                key={inst.id || i}
                                style={{
                                  display: 'flex',
                                  justifyContent: 'space-between',
                                  fontSize: '0.75rem',
                                  padding: '0.2rem 0',
                                  borderBottom: i < agr.installments.length - 1 ? '1px dashed #e2e8f0' : 'none'
                                }}
                              >
                                <span>#{inst.installment_number}: ETB {Number(inst.amount).toLocaleString()}</span>
                                <span style={{ color: inst.status === 'PAID' ? '#16a34a' : '#d97706', fontWeight: 600 }}>
                                  {inst.due_date} ({inst.status})
                                </span>
                              </div>
                            ))}
                          </td>
                          <td style={{ fontSize: '0.75rem', color: '#64748b', maxWidth: '180px' }}>
                            {agr.member_reason || 'N/A'}
                          </td>
                        </tr>
                      ))}
                      {(!overdueMonitoring?.agreements || overdueMonitoring.agreements.length === 0) && (
                        <tr>
                          <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                            No active payment agreements currently registered for this group.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Overdue Cases Table */}
              <div className="tre-card">
                <div className="tre-card-header">
                  <div>
                    <h3 className="tre-card-title">Monitored Overdue Obligations</h3>
                    <p className="tre-hero-sub">
                      All contribution obligations currently flagged as overdue across group members.
                    </p>
                  </div>
                </div>

                <div className="tre-table-responsive">
                  <table className="tre-table">
                    <thead>
                      <tr>
                        <th>Member</th>
                        <th>Amount Overdue</th>
                        <th>Original Deadline</th>
                        <th>Days Overdue</th>
                        <th>Grace Status</th>
                        <th>Current Resolution</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(overdueMonitoring?.overdue_cases || []).map((c) => (
                        <tr key={c.id}>
                          <td style={{ fontWeight: 700 }}>
                            <div>{c.member_name}</div>
                            <div style={{ fontSize: '0.72rem', color: '#64748b' }}>{c.member_email}</div>
                          </td>
                          <td style={{ fontWeight: 800, color: '#dc2626' }}>
                            ETB {Number(c.amount_overdue || 0).toLocaleString()}
                          </td>
                          <td>{c.original_deadline}</td>
                          <td>{c.days_overdue || 0} days</td>
                          <td>
                            {c.grace_period_expired ? (
                              <span className="tre-badge tre-badge-red">Expired</span>
                            ) : (
                              <span className="tre-badge tre-badge-orange">Grace Active</span>
                            )}
                          </td>
                          <td>
                            <span className="tre-badge tre-badge-blue">{c.status}</span>
                          </td>
                        </tr>
                      ))}
                      {(!overdueMonitoring?.overdue_cases || overdueMonitoring.overdue_cases.length === 0) && (
                        <tr>
                          <td colSpan="6" style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                            No overdue obligations. All active members are in good standing!
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Tab 7: Payouts Management */}
          {activeTab === 'payouts' && (
            <div className="tre-card">
              <div className="tre-card-header">
                <div>
                  <h2 className="tre-card-title">Rotation Payouts & Disbursements</h2>
                  <p className="tre-hero-sub">
                    Available Verified Group Funds: <strong style={{ color: '#10b981' }}>ETB {Number(payoutsData?.available_funds_etb || 0).toLocaleString()}</strong>
                  </p>
                </div>
                <button className="tre-btn-primary" onClick={() => setShowRequestPayoutModal(true)}>
                  + Prepare Payout Request
                </button>
              </div>

              <div className="tre-table-container">
                <table className="tre-table">
                  <thead>
                    <tr>
                      <th>Recipient</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Settlement</th>
                      <th>Requested By</th>
                      <th>Executed By</th>
                      <th>Reference</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payoutsData?.payouts?.map((po) => (
                      <tr key={po.id}>
                        <td style={{ fontWeight: 600 }}>{po.recipient_name}</td>
                        <td style={{ fontWeight: 700 }}>ETB {po.amount?.toLocaleString()}</td>
                        <td>
                          <span className={`tre-status-badge ${po.status === 'COMPLETED' ? 'confirmed' : 'pending'}`}>
                            {po.status}
                          </span>
                        </td>
                        <td>{po.settlement_status}</td>
                        <td>{po.requested_by}</td>
                        <td>{po.executed_by || '-'}</td>
                        <td style={{ fontFamily: 'monospace' }}>{po.execution_reference || '-'}</td>
                        <td>
                          {po.status === 'APPROVED' && (
                            <button
                              className="tre-btn-primary"
                              style={{ padding: '0.3rem 0.6rem', fontSize: '0.75rem' }}
                              onClick={() => { setExecutePayoutTarget(po); setShowExecutePayoutModal(true); }}
                            >
                              Execute
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 8: Financial Reports */}
          {activeTab === 'reports' && (
            <div className="tre-card">
              <div className="tre-card-header">
                <div>
                  <h2 className="tre-card-title">Financial Accounting Reports & Audits</h2>
                  <p className="tre-hero-sub">Downloadable statements with spreadsheet formula injection protection.</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <a
                    href={`/api/v1/treasurer/groups/${selectedGroupId || assignedGroups[0]?.id}/reports/export/?type=contributions`}
                    className="tre-btn-secondary"
                    style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}
                    download
                  >
                    <Download size={14} /> Export Contributions CSV
                  </a>
                  <a
                    href={`/api/v1/treasurer/groups/${selectedGroupId || assignedGroups[0]?.id}/reports/export/?type=ledger`}
                    className="tre-btn-secondary"
                    style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.8rem' }}
                    download
                  >
                    <Download size={14} /> Export Double-Entry Ledger
                  </a>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginTop: '1rem' }}>
                <div style={{ padding: '1rem', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Verified Available Balance</span>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#10b981', marginTop: '0.25rem' }}>
                    ETB {reportsData?.available_funds_etb?.toLocaleString() || '185,000'}
                  </div>
                </div>
                <div style={{ padding: '1rem', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Total Payouts Disbursed</span>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#2563eb', marginTop: '0.25rem' }}>
                    ETB {reportsData?.total_payouts_disbursed_etb?.toLocaleString() || '0'}
                  </div>
                </div>
                <div style={{ padding: '1rem', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>Overdue Obligations</span>
                  <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#ef4444', marginTop: '0.25rem' }}>
                    {reportsData?.overdue_obligations?.length || 0} Members
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tab 9: Notifications */}
          {activeTab === 'notifications' && (
            <div className="tre-card">
              <div className="tre-card-header">
                <h2 className="tre-card-title">Financial Audit & Activity Alerts</h2>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {Array.isArray(notificationsList) && notificationsList.length > 0 ? (
                  notificationsList.map((notif) => (
                    <div key={notif.id} style={{ padding: '1rem', border: '1px solid #e2e8f0', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div>
                        <h4 style={{ margin: 0, fontSize: '0.9rem', fontWeight: 700 }}>
                          {language === 'am' && notif.title_am ? notif.title_am : notif.title}
                        </h4>
                        <p style={{ margin: '0.25rem 0 0', fontSize: '0.82rem', color: '#64748b' }}>
                          {language === 'am' && notif.message_am ? notif.message_am : notif.message}
                        </p>
                      </div>
                      <span className="tre-status-badge pending">{notif.notification_type}</span>
                    </div>
                  ))
                ) : (
                  <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b', fontSize: '0.88rem' }}>
                    No notifications or financial alerts at this time.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tab 10: Settings */}
          {activeTab === 'settings' && (
            <div className="tre-card" style={{ maxWidth: '640px' }}>
              <div className="tre-card-header">
                <div>
                  <h2 className="tre-card-title">{t('treNavSettings') || 'Treasurer Profile & Credentials'}</h2>
                  <p style={{ fontSize: '0.82rem', color: 'var(--tre-text-muted, #64748b)', marginTop: '0.2rem' }}>
                    Update your treasurer name, phone number, profile photo, and account password.
                  </p>
                </div>
              </div>

              <form onSubmit={handleSaveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginTop: '1rem' }}>
                {/* Profile Photo Upload & Preview */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', padding: '1.25rem', background: 'var(--tre-card-bg, #ffffff)', borderRadius: '12px', border: '1px solid var(--tre-border, #e2e8f0)', flexWrap: 'wrap' }}>
                  <div style={{ position: 'relative', width: '70px', height: '70px', borderRadius: '50%', overflow: 'hidden', border: '2px solid #2563eb', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#eff6ff' }}>
                    {profileForm.avatar ? (
                      <img src={profileForm.avatar} alt="Profile" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                    ) : (
                      <span style={{ fontSize: '1.4rem', fontWeight: 800, color: '#2563eb' }}>
                        {profileForm.full_name ? profileForm.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : 'TR'}
                      </span>
                    )}
                  </div>
                  <div style={{ flex: 1, minWidth: '220px' }}>
                    <div style={{ fontSize: '0.98rem', fontWeight: 800, color: 'var(--tre-text-main, #0f172a)' }}>
                      {profileForm.full_name || 'Group Treasurer'}
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--tre-text-muted, #64748b)', marginBottom: '0.65rem' }}>
                      Financial Custodian • {user?.email}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                      <label className="btn btn-primary" style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.4rem' }}>
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
                                (dataUrl) => setProfileForm(prev => ({ ...prev, avatar: dataUrl })),
                                (errMsg) => setErrorMessage(errMsg)
                              );
                            }
                          }}
                        />
                      </label>
                      {profileForm.avatar && (
                        <button
                          type="button"
                          className="btn btn-secondary"
                          style={{ padding: '0.4rem 0.85rem', fontSize: '0.8rem', color: '#ef4444' }}
                          onClick={() => setProfileForm(prev => ({ ...prev, avatar: '' }))}
                        >
                          Remove Photo
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                <div className="tre-form-group">
                  <label className="tre-form-label">Full Name *</label>
                  <input
                    type="text"
                    required
                    className="tre-form-input"
                    value={profileForm.full_name}
                    onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })}
                  />
                </div>

                <div className="tre-form-group">
                  <label className="tre-form-label">Treasurer Account Email (Read-Only)</label>
                  <input
                    type="email"
                    className="tre-form-input"
                    value={user?.email || profileForm.email || ''}
                    disabled
                    readOnly
                    style={{ background: 'var(--bg-secondary, #f1f5f9)', cursor: 'not-allowed', opacity: 0.8 }}
                  />
                  <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '0.25rem' }}>
                    Primary identifier permanently tied to your treasurer account identity. Email cannot be changed.
                  </div>
                </div>

                <div className="tre-form-group">
                  <label className="tre-form-label">Phone Number</label>
                  <input
                    type="text"
                    className="tre-form-input"
                    placeholder="+251 91 123 4567"
                    value={profileForm.phone_number}
                    onChange={(e) => setProfileForm({ ...profileForm, phone_number: e.target.value })}
                  />
                </div>

                <div className="tre-form-group">
                  <label className="tre-form-label">Interface & Notification Language</label>
                  <select
                    className="tre-form-input"
                    value={profileForm.preferred_language || 'en'}
                    onChange={(e) => {
                      setProfileForm({ ...profileForm, preferred_language: e.target.value });
                      setLanguage(e.target.value);
                    }}
                  >
                    <option value="en">English (US)</option>
                    <option value="am">አማርኛ (Amharic)</option>
                    <option value="om">Afaan Oromoo (Oromo)</option>
                    <option value="ti">ትግርኛ (Tigrinya)</option>
                  </select>
                </div>

                {/* Password Change Box */}
                <div style={{ padding: '1.1rem', background: 'var(--tre-card-bg, #ffffff)', borderRadius: '10px', border: '1px solid var(--tre-border, #e2e8f0)' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.9rem', cursor: 'pointer', marginBottom: profileForm.change_password ? '0.85rem' : '0' }}>
                    <input
                      type="checkbox"
                      checked={profileForm.change_password}
                      onChange={(e) => setProfileForm({ ...profileForm, change_password: e.target.checked })}
                    />
                    <span>Change Account Password</span>
                  </label>

                  {profileForm.change_password && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginTop: '0.65rem' }}>
                      <div>
                        <label className="tre-form-label">Current Password *</label>
                        <input
                          type="password"
                          required
                          className="tre-form-input"
                          value={profileForm.current_password}
                          onChange={(e) => setProfileForm({ ...profileForm, current_password: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="tre-form-label">New Password (min 8 characters) *</label>
                        <input
                          type="password"
                          required
                          className="tre-form-input"
                          value={profileForm.new_password}
                          onChange={(e) => setProfileForm({ ...profileForm, new_password: e.target.value })}
                        />
                      </div>
                      <div>
                        <label className="tre-form-label">Confirm New Password *</label>
                        <input
                          type="password"
                          required
                          className="tre-form-input"
                          value={profileForm.confirm_new_password}
                          onChange={(e) => setProfileForm({ ...profileForm, confirm_new_password: e.target.value })}
                        />
                      </div>
                    </div>
                  )}
                </div>

                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={profileSaving}
                  style={{ alignSelf: 'flex-start', padding: '0.65rem 1.5rem', fontWeight: 700 }}
                >
                  {profileSaving ? 'Saving Changes...' : 'Save Profile Changes'}
                </button>
              </form>
            </div>
          )}

          {/* Tab 11: Help & Support */}
          {activeTab === 'help' && (
            <div className="tre-card">
              <div className="tre-card-header">
                <h2 className="tre-card-title">Treasurer Operating Guidelines & Help</h2>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.88rem', color: '#334155' }}>
                <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontWeight: 700 }}>Dual Custody Cash Handling Protocol</h4>
                  <p>When cash is recorded in-person by an authorized Treasurer or Organizer, group bylaws require a second independent sign-off before the balance is credited to the official group ledger.</p>
                </div>
                <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '8px' }}>
                  <h4 style={{ margin: '0 0 0.5rem', fontWeight: 700 }}>Bank & Telebirr Transfer Reconciliation</h4>
                  <p>Members who transfer via commercial banks or Telebirr submit transaction references. The Treasurer must cross-reference against bank statements before confirming.</p>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ================= MODALS ================= */}

      {/* 1. Record Cash Receipt Modal */}
      {showRecordCashModal && (
        <div className="tre-modal-backdrop">
          <div className="tre-modal-card">
            <div className="tre-modal-header">
              <h3 className="tre-modal-title">Record In-Person Cash Receipt</h3>
              <button className="tre-modal-close-btn" onClick={() => setShowRecordCashModal(false)}>✕</button>
            </div>
            <form onSubmit={handleRecordCashSubmit}>
              <div className="tre-modal-body">
                <div className="tre-form-group">
                  <label className="tre-form-label">Contribution Obligation ID *</label>
                  <input
                    type="text"
                    className="tre-form-input"
                    placeholder="Enter UUID of member's obligation"
                    value={recordCashForm.obligation_id}
                    onChange={(e) => setRecordCashForm({ ...recordCashForm, obligation_id: e.target.value })}
                    required
                  />
                </div>
                <div className="tre-form-group">
                  <label className="tre-form-label">Amount (ETB) *</label>
                  <input
                    type="number"
                    step="0.01"
                    className="tre-form-input"
                    placeholder="e.g. 5000.00"
                    value={recordCashForm.amount}
                    onChange={(e) => setRecordCashForm({ ...recordCashForm, amount: e.target.value })}
                    required
                  />
                </div>
                <div className="tre-form-group">
                  <label className="tre-form-label">Physical Receipt # (Optional)</label>
                  <input
                    type="text"
                    className="tre-form-input"
                    placeholder="Leave blank to auto-generate"
                    value={recordCashForm.receipt_number}
                    onChange={(e) => setRecordCashForm({ ...recordCashForm, receipt_number: e.target.value })}
                  />
                </div>
                <div className="tre-form-group">
                  <label className="tre-form-label">Notes</label>
                  <textarea
                    className="tre-form-textarea"
                    rows="2"
                    placeholder="e.g. Paid in cash at weekly market meeting"
                    value={recordCashForm.notes}
                    onChange={(e) => setRecordCashForm({ ...recordCashForm, notes: e.target.value })}
                  />
                </div>
              </div>
              <div className="tre-modal-footer">
                <button type="button" className="tre-btn-secondary" onClick={() => setShowRecordCashModal(false)}>Cancel</button>
                <button type="submit" className="tre-btn-primary" disabled={actionLoading}>
                  {actionLoading ? 'Recording...' : 'Record Cash'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 2. Printable Receipt Modal */}
      {showPrintReceiptModal && activePrintReceipt && (
        <div className="tre-modal-backdrop">
          <div className="tre-modal-card">
            <div className="tre-modal-header">
              <h3 className="tre-modal-title">Official Cash Receipt</h3>
              <button className="tre-modal-close-btn" onClick={() => setShowPrintReceiptModal(false)}>✕</button>
            </div>
            <div className="tre-modal-body">
              <div className="tre-printable-receipt">
                <div className="tre-receipt-header">
                  <div className="tre-receipt-seal">DIGITAL EQUB OFFICIAL RECEIPT</div>
                  <h4 style={{ margin: '0.25rem 0', fontWeight: 800 }}>{activePrintReceipt.group_name}</h4>
                  <div style={{ fontSize: '0.78rem', color: '#64748b' }}>Receipt #: {activePrintReceipt.receipt_number}</div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.85rem' }}>
                  <div><strong>Member:</strong> {activePrintReceipt.member_name}</div>
                  <div><strong>Amount Paid:</strong> ETB {activePrintReceipt.amount_etb?.toLocaleString()}</div>
                  <div><strong>Round:</strong> Round {activePrintReceipt.period_round}</div>
                  <div><strong>Received By:</strong> {activePrintReceipt.received_by}</div>
                  <div><strong>Verified By:</strong> {activePrintReceipt.confirmed_by || 'Awaiting 2nd Check'}</div>
                  <div><strong>Date Issued:</strong> {activePrintReceipt.date_issued}</div>
                  <div><strong>Status:</strong> {activePrintReceipt.status}</div>
                </div>
              </div>
            </div>
            <div className="tre-modal-footer">
              <button className="tre-btn-secondary" onClick={() => window.print()}>
                <Printer size={16} style={{ marginRight: '0.4rem' }} /> Print Slip
              </button>
              <button className="tre-btn-primary" onClick={() => setShowPrintReceiptModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Reconcile Bank Transfer Modal */}
      {showReconcileModal && reconcileTarget && (
        <div className="tre-modal-backdrop">
          <div className="tre-modal-card">
            <div className="tre-modal-header">
              <h3 className="tre-modal-title">Reconcile Transfer: {reconcileTarget.transfer_reference}</h3>
              <button className="tre-modal-close-btn" onClick={() => setShowReconcileModal(false)}>✕</button>
            </div>
            <div className="tre-modal-body">
              <p style={{ fontSize: '0.88rem', color: '#475569' }}>
                Verify that <strong>ETB {reconcileTarget.amount?.toLocaleString()}</strong> from <strong>{reconcileTarget.member_name}</strong> has been credited to group bank accounts.
              </p>
              <div className="tre-form-group" style={{ marginTop: '1rem' }}>
                <label className="tre-form-label">Audit / Reconciliation Note</label>
                <textarea
                  className="tre-form-textarea"
                  rows="2"
                  placeholder="e.g. Verified on CBE statement line #4482"
                  value={reconcileNotes}
                  onChange={(e) => setReconcileNotes(e.target.value)}
                />
              </div>
            </div>
            <div className="tre-modal-footer">
              <button
                className="tre-btn-danger"
                onClick={() => handleReconcileActionSubmit('REJECT')}
                disabled={actionLoading}
              >
                Reject / Invalid
              </button>
              <button
                className="tre-btn-primary"
                onClick={() => handleReconcileActionSubmit('CONFIRM')}
                disabled={actionLoading}
              >
                {actionLoading ? 'Processing...' : 'Confirm & Credit'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 4. Flag Exception Modal */}
      {showFlagExceptionModal && (
        <div className="tre-modal-backdrop">
          <div className="tre-modal-card">
            <div className="tre-modal-header">
              <h3 className="tre-modal-title">Flag Reconciliation Exception</h3>
              <button className="tre-modal-close-btn" onClick={() => setShowFlagExceptionModal(false)}>✕</button>
            </div>
            <form onSubmit={handleFlagExceptionSubmit}>
              <div className="tre-modal-body">
                <div className="tre-form-group">
                  <label className="tre-form-label">Exception Type</label>
                  <select
                    className="tre-form-select"
                    value={flagExceptionForm.exception_type}
                    onChange={(e) => setFlagExceptionForm({ ...flagExceptionForm, exception_type: e.target.value })}
                  >
                    <option value="DUPLICATE_REFERENCE">Duplicate Reference</option>
                    <option value="AMOUNT_MISMATCH">Amount Mismatch</option>
                    <option value="WRONG_BENEFICIARY">Wrong Beneficiary</option>
                    <option value="UNIDENTIFIED_SENDER">Unidentified Sender</option>
                    <option value="SUSPECTED_FRAUD">Suspected Fraud</option>
                    <option value="OTHER">Other Discrepancy</option>
                  </select>
                </div>
                <div className="tre-form-group">
                  <label className="tre-form-label">Reference Number *</label>
                  <input
                    type="text"
                    className="tre-form-input"
                    placeholder="e.g. TXN-998822"
                    value={flagExceptionForm.reference_number}
                    onChange={(e) => setFlagExceptionForm({ ...flagExceptionForm, reference_number: e.target.value })}
                    required
                  />
                </div>
                <div className="tre-form-group">
                  <label className="tre-form-label">Description *</label>
                  <textarea
                    className="tre-form-textarea"
                    rows="3"
                    placeholder="Explain the discrepancy..."
                    value={flagExceptionForm.description}
                    onChange={(e) => setFlagExceptionForm({ ...flagExceptionForm, description: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="tre-modal-footer">
                <button type="button" className="tre-btn-secondary" onClick={() => setShowFlagExceptionModal(false)}>Cancel</button>
                <button type="submit" className="tre-btn-primary" disabled={actionLoading}>Flag Discrepancy</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 5. Approval Modal */}
      {showApprovalModal && approvalTarget && (
        <div className="tre-modal-backdrop">
          <div className="tre-modal-card">
            <div className="tre-modal-header">
              <h3 className="tre-modal-title">Sign Independent Approval</h3>
              <button className="tre-modal-close-btn" onClick={() => setShowApprovalModal(false)}>✕</button>
            </div>
            <div className="tre-modal-body">
              <p style={{ fontSize: '0.88rem' }}>
                Action: <strong>{approvalTarget.action_title}</strong><br />
                Amount: <strong>ETB {approvalTarget.amount?.toLocaleString()}</strong><br />
                Initiated by: <strong>{approvalTarget.initiator_name}</strong>
              </p>
              <div className="tre-form-group" style={{ marginTop: '1rem' }}>
                <label className="tre-form-label">Decision</label>
                <select
                  className="tre-form-select"
                  value={approvalDecision}
                  onChange={(e) => setApprovalDecision(e.target.value)}
                >
                  <option value="APPROVE">Approve & Sign</option>
                  <option value="REJECT">Reject</option>
                </select>
              </div>
              <div className="tre-form-group">
                <label className="tre-form-label">Justification / Reason</label>
                <textarea
                  className="tre-form-textarea"
                  rows="2"
                  placeholder="State your sign-off or rejection reason..."
                  value={approvalReason}
                  onChange={(e) => setApprovalReason(e.target.value)}
                />
              </div>
            </div>
            <div className="tre-modal-footer">
              <button className="tre-btn-secondary" onClick={() => setShowApprovalModal(false)}>Cancel</button>
              <button className="tre-btn-primary" onClick={handleApprovalActionSubmit} disabled={actionLoading}>
                {actionLoading ? 'Recording...' : 'Submit Decision'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. Request Payout Modal */}
      {showRequestPayoutModal && (
        <div className="tre-modal-backdrop">
          <div className="tre-modal-card">
            <div className="tre-modal-header">
              <h3 className="tre-modal-title">Prepare Rotation Payout Request</h3>
              <button className="tre-modal-close-btn" onClick={() => setShowRequestPayoutModal(false)}>✕</button>
            </div>
            <form onSubmit={handleRequestPayoutSubmit}>
              <div className="tre-modal-body">
                <div className="tre-form-group">
                  <label className="tre-form-label">Select Recipient Member *</label>
                  <select
                    className="tre-form-select"
                    value={requestPayoutForm.membership_id}
                    onChange={(e) => setRequestPayoutForm({ ...requestPayoutForm, membership_id: e.target.value })}
                    required
                  >
                    <option value="">-- Choose Eligible Member --</option>
                    {payoutsData?.eligible_recipients?.map((el) => (
                      <option key={el.membership_id} value={el.membership_id}>
                        {el.user_name} (Order #{el.order_index})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="tre-form-group">
                  <label className="tre-form-label">Payout Amount (ETB)</label>
                  <input
                    type="number"
                    step="0.01"
                    className="tre-form-input"
                    placeholder="Leave blank for standard round calculation"
                    value={requestPayoutForm.amount}
                    onChange={(e) => setRequestPayoutForm({ ...requestPayoutForm, amount: e.target.value })}
                  />
                </div>
              </div>
              <div className="tre-modal-footer">
                <button type="button" className="tre-btn-secondary" onClick={() => setShowRequestPayoutModal(false)}>Cancel</button>
                <button type="submit" className="tre-btn-primary" disabled={actionLoading}>Request Payout</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 7. Execute Payout Modal */}
      {showExecutePayoutModal && executePayoutTarget && (
        <div className="tre-modal-backdrop">
          <div className="tre-modal-card">
            <div className="tre-modal-header">
              <h3 className="tre-modal-title">Execute Payout Settlement</h3>
              <button className="tre-modal-close-btn" onClick={() => setShowExecutePayoutModal(false)}>✕</button>
            </div>
            <form onSubmit={handleExecutePayoutSubmit}>
              <div className="tre-modal-body">
                <p style={{ fontSize: '0.88rem' }}>
                  Executing payout of <strong>ETB {executePayoutTarget.amount?.toLocaleString()}</strong> to <strong>{executePayoutTarget.recipient_name}</strong>.<br />
                  This action will atomically debit the double-entry group ledger.
                </p>
                <div className="tre-form-group" style={{ marginTop: '1rem' }}>
                  <label className="tre-form-label">Bank / Telebirr Transaction Reference *</label>
                  <input
                    type="text"
                    className="tre-form-input"
                    placeholder="e.g. CBE-TX-998822 or Telebirr ID"
                    value={executionRef}
                    onChange={(e) => setExecutionRef(e.target.value)}
                    required
                  />
                </div>
                <div className="tre-form-group">
                  <label className="tre-form-label">Execution Notes</label>
                  <textarea
                    className="tre-form-textarea"
                    rows="2"
                    placeholder="Additional settlement remarks..."
                    value={executionNotes}
                    onChange={(e) => setExecutionNotes(e.target.value)}
                  />
                </div>
              </div>
              <div className="tre-modal-footer">
                <button type="button" className="tre-btn-secondary" onClick={() => setShowExecutePayoutModal(false)}>Cancel</button>
                <button type="submit" className="tre-btn-primary" disabled={actionLoading}>
                  {actionLoading ? 'Executing...' : 'Confirm Execution & Debit Ledger'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 8. Group Detail Drawer */}
      {showGroupDetailModal && selectedGroupDetail && (
        <div className="tre-modal-backdrop">
          <div className="tre-modal-card">
            <div className="tre-modal-header">
              <h3 className="tre-modal-title">{selectedGroupDetail.name} — Financial Audit</h3>
              <button className="tre-modal-close-btn" onClick={() => setShowGroupDetailModal(false)}>✕</button>
            </div>
            <div className="tre-modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.88rem' }}>
              <div><strong>Description:</strong> {selectedGroupDetail.description}</div>
              <div><strong>Organizer:</strong> {selectedGroupDetail.organizer_name}</div>
              <div><strong>Active Members:</strong> {selectedGroupDetail.members_count}</div>
              <div><strong>Monthly Contribution:</strong> ETB {selectedGroupDetail.contribution_amount?.toLocaleString()}</div>
              <div><strong>Available Treasury Funds:</strong> <span style={{ color: '#10b981', fontWeight: 800 }}>ETB {selectedGroupDetail.available_funds_etb?.toLocaleString()}</span></div>
              <div><strong>Current Period Round:</strong> Round {selectedGroupDetail.current_round}</div>
              <div style={{ marginTop: '0.5rem', padding: '0.75rem', background: selectedGroupDetail.chapa_subaccount_id ? '#f0fdf4' : '#eff6ff', borderRadius: '8px', border: `1px solid ${selectedGroupDetail.chapa_subaccount_id ? '#86efac' : '#bfdbfe'}` }}>
                <div style={{ fontWeight: 700, color: selectedGroupDetail.chapa_subaccount_id ? '#15803d' : '#1e40af', marginBottom: '0.25rem' }}>
                  🏦 Chapa Direct Settlement Account
                </div>
                {selectedGroupDetail.chapa_subaccount_id ? (
                  <div style={{ fontSize: '0.82rem', color: '#166534' }}>
                    Linked Bank: <strong>{selectedGroupDetail.bank_name || 'Commercial Bank of Ethiopia (CBE)'}</strong><br />
                    Account: <strong>{selectedGroupDetail.bank_account_number}</strong> ({selectedGroupDetail.bank_account_name})<br />
                    Subaccount ID: <code style={{ fontSize: '0.75rem' }}>{selectedGroupDetail.chapa_subaccount_id}</code>
                  </div>
                ) : (
                  <div style={{ fontSize: '0.82rem', color: '#64748b' }}>
                    No dedicated Chapa subaccount linked. Funds are tracked directly on the group common treasury ledger.
                  </div>
                )}
              </div>
            </div>
            <div className="tre-modal-footer">
              <button className="tre-btn-primary" onClick={() => setShowGroupDetailModal(false)}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* 9. Make Personal Contribution Payment Modal */}
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
                    🛡️ Group funds belong exclusively to your Equb group and remain strictly isolated from platform rent.
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
                As the group treasurer, you can allocate your cash contribution directly to the group cash box and record it in the <strong>Cash Receipts Register</strong> for dual-confirmation.
              </div>
            )}

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="tre-btn-secondary"
                onClick={() => setShowPersonalPaymentModal(false)}
                style={{ padding: '0.6rem 1.2rem', borderRadius: '8px', cursor: 'pointer' }}
              >
                Cancel
              </button>
              {personalPaymentMethod !== 'CASH' && (
                <button
                  type="button"
                  className="tre-btn-primary"
                  onClick={handleExecutePersonalPayment}
                  disabled={payingPersonalObligation}
                  style={{ padding: '0.6rem 1.2rem', borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                >
                  {payingPersonalObligation && <RefreshCw size={16} className="tre-spin" />}
                  <span>Confirm & Submit Payment</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
      {/* Bidirectional Chat Widget with Organizer */}
      <ChatWidget currentUser={user} />
    </div>
  );
}
