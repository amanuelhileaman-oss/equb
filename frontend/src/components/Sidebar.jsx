import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { NotificationCenter } from './NotificationCenter';
import { 
  ShieldCheck, 
  Users, 
  Landmark, 
  UserCheck, 
  Globe, 
  LogOut, 
  Layers,
  X
} from 'lucide-react';

export function Sidebar({ isOpen, onClose }) {
  const { user, groupRoles, currentInterface, setCurrentInterface, selectedGroupId, setSelectedGroupId, logout } = useAuth();
  const { language, toggleLanguage, t } = useLanguage();

  if (!user) return null;

  const isPlatformAdmin = Boolean(user.is_platform_admin);
  const isOrganizer = !isPlatformAdmin && Boolean(user.is_organizer || user.has_organizer_profile || user.primary_role === 'ORGANIZER' || groupRoles.some(gr => gr.roles.includes('GROUP_ORGANIZER')));
  const isTreasurer = !isPlatformAdmin && !isOrganizer && Boolean(user.is_treasurer || user.primary_role === 'TREASURER' || groupRoles.some(gr => gr.roles.includes('GROUP_TREASURER')));
  const isMember = !isPlatformAdmin && (user.primary_role === 'MEMBER' || (!isOrganizer && !isTreasurer) || groupRoles.some(gr => gr.roles.includes('GROUP_MEMBER')));

  const handleSelectInterface = (portalKey) => {
    setCurrentInterface(portalKey);
    if (onClose) onClose();
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div 
          className="sidebar-backdrop" 
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside className={`app-sidebar ${isOpen ? 'open' : ''}`}>
        
        {/* Brand / Logo */}
        <div className="sidebar-brand">
          <div style={{ 
            width: '38px', 
            height: '38px', 
            borderRadius: '10px', 
            background: 'linear-gradient(135deg, #10b981 0%, #f59e0b 50%, #ef4444 100%)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)',
            flexShrink: 0
          }}>
            <Layers size={20} color="#ffffff" />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 800, fontSize: '1.05rem', color: '#ffffff', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span>{t('brandName')}</span>
              <span className="badge badge-green" style={{ fontSize: '0.6rem', padding: '0.1rem 0.4rem' }}>MVP</span>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {t('tagline')}
            </div>
          </div>
          {/* Close button for mobile */}
          <button 
            type="button"
            onClick={onClose}
            className="btn btn-secondary mobile-only-btn"
            style={{ padding: '0.35rem', borderRadius: 'var(--radius-sm)' }}
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Active Group Selector */}
        {groupRoles.length > 0 && currentInterface !== 'SUPER_ADMIN' && (
          <div style={{ marginBottom: '1.25rem' }}>
            <div className="sidebar-section-label">
              {language === 'am' ? 'ንቁ ዕቁብ' : 'ACTIVE EQUB GROUP'}
            </div>
            <select
              id="active-group-select"
              className="form-select"
              style={{ width: '100%', padding: '0.55rem 0.85rem', fontSize: '0.825rem' }}
              value={selectedGroupId || ''}
              onChange={(e) => setSelectedGroupId(e.target.value)}
            >
              {groupRoles.map(gr => (
                <option key={gr.group_id} value={gr.group_id}>
                  {gr.group_name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Vertical Portals Navigation */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          <div className="sidebar-section-label">
            {language === 'am' ? 'የመድረክ ክፍሎች (PORTALS)' : 'PORTAL INTERFACES'}
          </div>

          <div className="vertical-nav-container">
            {isPlatformAdmin && (
              <button
                id="nav-super-admin"
                type="button"
                className={`nav-tab-vertical ${currentInterface === 'SUPER_ADMIN' ? 'active' : ''}`}
                onClick={() => handleSelectInterface('SUPER_ADMIN')}
                title={t('roleSuperAdmin')}
              >
                <div className="nav-tab-icon">
                  <ShieldCheck size={18} color={currentInterface === 'SUPER_ADMIN' ? '#10b981' : '#9ca3af'} />
                </div>
                <div className="nav-tab-content">
                  <div className="nav-tab-title">{t('roleSuperAdmin')}</div>
                  <div className="nav-tab-desc">
                    {language === 'am' ? 'የመድረክ ቁጥጥርና አመራር' : 'Platform Governance & SaaS'}
                  </div>
                </div>
                {currentInterface === 'SUPER_ADMIN' && <div className="nav-tab-active-indicator" />}
              </button>
            )}

            {isOrganizer && (
              <button
                id="nav-organizer"
                type="button"
                className={`nav-tab-vertical ${currentInterface === 'ORGANIZER' ? 'active' : ''}`}
                onClick={() => handleSelectInterface('ORGANIZER')}
                title={t('roleOrganizer')}
              >
                <div className="nav-tab-icon">
                  <Users size={18} color={currentInterface === 'ORGANIZER' ? '#10b981' : '#9ca3af'} />
                </div>
                <div className="nav-tab-content">
                  <div className="nav-tab-title">{t('roleOrganizer')}</div>
                  <div className="nav-tab-desc">
                    {language === 'am' ? 'ዕቁብ ማደራጀትና ደንቦች' : 'Equb Management & Rules'}
                  </div>
                </div>
                {currentInterface === 'ORGANIZER' && <div className="nav-tab-active-indicator" />}
              </button>
            )}

            {isTreasurer && (
              <button
                id="nav-treasurer"
                type="button"
                className={`nav-tab-vertical ${currentInterface === 'TREASURER' ? 'active' : ''}`}
                onClick={() => handleSelectInterface('TREASURER')}
                title={t('roleTreasurer')}
              >
                <div className="nav-tab-icon">
                  <Landmark size={18} color={currentInterface === 'TREASURER' ? '#10b981' : '#9ca3af'} />
                </div>
                <div className="nav-tab-content">
                  <div className="nav-tab-title">{t('roleTreasurer')}</div>
                  <div className="nav-tab-desc">
                    {language === 'am' ? 'የገንዘብ እንቅስቃሴና ክፍያዎች' : 'Ledger, Cash & Payouts'}
                  </div>
                </div>
                {currentInterface === 'TREASURER' && <div className="nav-tab-active-indicator" />}
              </button>
            )}

            {isMember && (
              <button
                id="nav-member"
                type="button"
                className={`nav-tab-vertical ${currentInterface === 'MEMBER' ? 'active' : ''}`}
                onClick={() => handleSelectInterface('MEMBER')}
                title={t('roleMember')}
              >
                <div className="nav-tab-icon">
                  <UserCheck size={18} color={currentInterface === 'MEMBER' ? '#10b981' : '#9ca3af'} />
                </div>
                <div className="nav-tab-content">
                  <div className="nav-tab-title">{t('roleMember')}</div>
                  <div className="nav-tab-desc">
                    {language === 'am' ? 'መዋጮና ዕጣ መቀበያ' : 'Contributions & Draw Payouts'}
                  </div>
                </div>
                {currentInterface === 'MEMBER' && <div className="nav-tab-active-indicator" />}
              </button>
            )}
          </div>
        </div>

        {/* Sidebar Footer: Notifications, Language Toggle, User Profile Card & Logout */}
        <div className="sidebar-footer">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <NotificationCenter />
            <button
              id="lang-toggle-btn"
              type="button"
              onClick={toggleLanguage}
              className="btn btn-secondary"
              style={{ flex: 1, justifyContent: 'center', gap: '0.5rem', padding: '0.55rem' }}
              title="Switch Language / ቋንቋ ቀይር"
            >
              <Globe size={16} color="#f59e0b" />
              <span style={{ fontWeight: 700 }}>{language === 'en' ? 'አማርኛ' : 'English'}</span>
            </button>
          </div>

          <div className="sidebar-user-card">
            <div className="user-avatar">
              {user.full_name?.charAt(0) || 'U'}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.full_name}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {user.email}
              </div>
            </div>
            <button
              id="logout-btn"
              type="button"
              onClick={logout}
              className="btn-icon-danger"
              title={t('logout')}
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>

      </aside>
    </>
  );
}
