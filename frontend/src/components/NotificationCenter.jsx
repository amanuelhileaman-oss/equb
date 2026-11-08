import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import {
  Bell,
  CheckCheck,
  AlertCircle,
  CheckCircle2,
  DollarSign,
  FileText,
  Clock,
  RefreshCw
} from 'lucide-react';
import './NotificationCenter.css';

export function NotificationCenter({ className = '' }) {
  const { language, t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);

  const getLabel = (key) => {
    const labels = {
      title: {
        en: 'Notifications',
        am: 'ማሳወቂያዎች',
        om: 'Beeksisa',
        ti: 'መልእኽትታት'
      },
      markAllRead: {
        en: 'Mark all as read',
        am: 'ሁሉንም አንብብ',
        om: 'Hunda dubbisi',
        ti: 'ኩሉ ኣንብብ'
      },
      empty: {
        en: 'No notifications yet',
        am: 'ምንም ማሳወቂያ የለም',
        om: 'Beeksisi hin jiru',
        ti: 'ምንም መልእኽቲ የለን'
      },
      newBadge: {
        en: 'new',
        am: 'አዲስ',
        om: 'haaraa',
        ti: 'ሓድሽ'
      },
      loading: {
        en: 'Loading notifications...',
        am: 'ማሳወቂያዎች በመጫን ላይ...',
        om: 'Beeksisni fe\'amaa jira...',
        ti: 'መልእኽትታት ይጽዓን ኣሎ...'
      }
    };
    return labels[key]?.[language] || labels[key]?.en || '';
  };

  const fetchNotifications = async (quiet = false) => {
    try {
      if (!quiet) setLoading(true);
      const data = await api.getNotifications();
      if (data) {
        setNotifications(data.results || []);
        setUnreadCount(data.unread_count || 0);
      }
    } catch (err) {
      console.warn('Failed to load notifications:', err);
    } finally {
      if (!quiet) setLoading(false);
    }
  };

  // Initial fetch and 30s background polling
  useEffect(() => {
    fetchNotifications(true);
    const interval = setInterval(() => fetchNotifications(true), 30000);
    return () => clearInterval(interval);
  }, []);

  // Close when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('touchstart', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [isOpen]);

  // Click handler on the Bell Button:
  // "it must be have red mark inside their and after click them the notfications color must be gone"
  const handleToggleBell = async () => {
    const nextOpen = !isOpen;
    setIsOpen(nextOpen);

    if (nextOpen) {
      // If there were unread notifications, immediately clear the red badge mark
      if (unreadCount > 0) {
        setUnreadCount(0);
        setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
        try {
          await api.markAllNotificationsRead();
        } catch (err) {
          console.warn('Failed to mark all as read on open:', err);
        }
      }
      fetchNotifications(true);
    }
  };

  const handleMarkAsRead = async (id, e) => {
    if (e) e.stopPropagation();
    try {
      await api.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.warn('Failed to mark notification as read:', err);
    }
  };

  const handleMarkAllRead = async (e) => {
    if (e) e.stopPropagation();
    try {
      setUnreadCount(0);
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      await api.markAllNotificationsRead();
    } catch (err) {
      console.warn('Failed to mark all as read:', err);
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'PAYMENT_RECEIVED':
      case 'PAYOUT_EXECUTED':
        return <CheckCircle2 size={16} color="#10b981" />;
      case 'CONTRIBUTION_DUE':
      case 'CASH_VERIFICATION_REQUEST':
      case 'BANK_RECONCILIATION_REQUEST':
        return <DollarSign size={16} color="#f59e0b" />;
      case 'RULE_PROPOSAL':
      case 'RULE_APPROVED':
        return <FileText size={16} color="#3b82f6" />;
      case 'DISPUTE_FILED':
        return <AlertCircle size={16} color="#ef4444" />;
      default:
        return <Bell size={16} color="#9ca3af" />;
    }
  };

  const formatTimestamp = (dateStr) => {
    if (!dateStr) return '';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString(language === 'am' ? 'am-ET' : 'en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className={`notif-center-wrapper ${className}`} ref={dropdownRef}>
      {/* Bell Button */}
      <button
        id="notification-bell-btn"
        type="button"
        onClick={handleToggleBell}
        className={`notif-bell-btn ${isOpen ? 'active' : ''}`}
        aria-label={getLabel('title')}
        title={getLabel('title')}
      >
        <Bell size={19} />
        {/* Red Mark / Unread count indicator: shown only when unreadCount > 0 */}
        {unreadCount > 0 && (
          <span className="notif-badge-red" title={`${unreadCount} unread`}>
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Floating Notification Popover */}
      {isOpen && (
        <div className="notif-popover">
          {/* Header */}
          <div className="notif-popover-header">
            <div className="notif-header-title">
              <Bell size={17} color="#2563eb" />
              <span>{getLabel('title')}</span>
              {unreadCount > 0 && (
                <span
                  style={{
                    fontSize: '0.68rem',
                    background: '#ef4444',
                    color: '#fff',
                    padding: '0.1rem 0.4rem',
                    borderRadius: '10px',
                    fontWeight: 700
                  }}
                >
                  {unreadCount} {getLabel('newBadge')}
                </span>
              )}
            </div>

            <div className="notif-header-actions">
              <button
                type="button"
                className="notif-header-btn"
                onClick={() => fetchNotifications(false)}
                title="Refresh notifications"
              >
                <RefreshCw size={13} className={loading ? 'org-spin' : ''} />
              </button>
              {notifications.some((n) => !n.is_read) && (
                <button
                  type="button"
                  className="notif-header-btn"
                  onClick={handleMarkAllRead}
                >
                  <CheckCheck size={14} />
                  <span>{getLabel('markAllRead')}</span>
                </button>
              )}
            </div>
          </div>

          {/* List */}
          <div className="notif-list-body">
            {loading && notifications.length === 0 ? (
              <div
                style={{
                  padding: '2rem',
                  textAlign: 'center',
                  color: 'var(--text-muted, #64748b)',
                  fontSize: '0.85rem'
                }}
              >
                {getLabel('loading')}
              </div>
            ) : notifications.length === 0 ? (
              <div
                style={{
                  padding: '2.5rem 1rem',
                  textAlign: 'center',
                  color: 'var(--text-muted, #94a3b8)'
                }}
              >
                <Bell size={30} style={{ opacity: 0.3, margin: '0 auto 0.5rem' }} />
                <div style={{ fontSize: '0.86rem', fontWeight: 600 }}>
                  {getLabel('empty')}
                </div>
              </div>
            ) : (
              notifications.map((n) => {
                const title =
                  language === 'am' ? n.title_am || n.title : n.title;
                const message =
                  language === 'am' ? n.message_am || n.message : n.message;
                return (
                  <div
                    key={n.id}
                    className={`notif-item ${!n.is_read ? 'unread' : ''}`}
                    onClick={() =>
                      !n.is_read && handleMarkAsRead(n.id)
                    }
                  >
                    <div className="notif-item-icon">
                      {getTypeIcon(n.notification_type)}
                    </div>
                    <div className="notif-item-content">
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '0.5rem'
                        }}
                      >
                        <div className="notif-item-title">{title}</div>
                        {!n.is_read && <span className="notif-unread-dot" />}
                      </div>
                      <div className="notif-item-message">{message}</div>
                      <div className="notif-item-meta">
                        <Clock size={11} />
                        <span>{formatTimestamp(n.created_at)}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default NotificationCenter;
