import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { 
  ShieldCheck, 
  Users, 
  Landmark, 
  UserCheck, 
  Globe, 
  LogOut, 
  Layers
} from 'lucide-react';

export function Navbar() {
  const { user, groupRoles, currentInterface, setCurrentInterface, selectedGroupId, setSelectedGroupId, logout } = useAuth();
  const { language, toggleLanguage, t } = useLanguage();

  if (!user) return null;

  const isPlatformAdmin = Boolean(user.is_platform_admin);
  const isOrganizer = !isPlatformAdmin && Boolean(user.is_organizer || user.has_organizer_profile || user.primary_role === 'ORGANIZER' || groupRoles.some(gr => gr.roles.includes('GROUP_ORGANIZER')));
  const isTreasurer = !isPlatformAdmin && !isOrganizer && Boolean(user.is_treasurer || user.primary_role === 'TREASURER' || groupRoles.some(gr => gr.roles.includes('GROUP_TREASURER')));

  return (
    <header className="glass" style={{ position: 'sticky', top: 0, zIndex: 100, borderBottom: '1px solid var(--border-color)' }}>
      <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '0.85rem 1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        
        {/* Brand / Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            borderRadius: '12px', 
            background: 'linear-gradient(135deg, #10b981 0%, #f59e0b 50%, #ef4444 100%)', 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            boxShadow: '0 4px 14px rgba(16, 185, 129, 0.35)'
          }}>
            <Layers size={22} color="#ffffff" />
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.15rem', color: '#ffffff', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              {t('brandName')}
              <span className="badge badge-green" style={{ fontSize: '0.65rem', padding: '0.15rem 0.5rem' }}>MVP</span>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {t('tagline')}
            </div>
          </div>
        </div>

        {/* Four Main Interface Switcher Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', background: 'rgba(0,0,0,0.3)', padding: '0.25rem', borderRadius: 'var(--radius-md)' }}>
          {isPlatformAdmin && (
            <button
              id="nav-super-admin"
              className={`nav-tab ${currentInterface === 'SUPER_ADMIN' ? 'active' : ''}`}
              onClick={() => setCurrentInterface('SUPER_ADMIN')}
              title={t('roleSuperAdmin')}
            >
              <ShieldCheck size={16} color={currentInterface === 'SUPER_ADMIN' ? '#10b981' : 'currentColor'} />
              <span>{t('roleSuperAdmin')}</span>
            </button>
          )}

          {isOrganizer && (
            <button
              id="nav-organizer"
              className={`nav-tab ${currentInterface === 'ORGANIZER' ? 'active' : ''}`}
              onClick={() => setCurrentInterface('ORGANIZER')}
              title={t('roleOrganizer')}
            >
              <Users size={16} color={currentInterface === 'ORGANIZER' ? '#10b981' : 'currentColor'} />
              <span>{t('roleOrganizer')}</span>
            </button>
          )}

          {isTreasurer && (
            <button
              id="nav-treasurer"
              className={`nav-tab ${currentInterface === 'TREASURER' ? 'active' : ''}`}
              onClick={() => setCurrentInterface('TREASURER')}
              title={t('roleTreasurer')}
            >
              <Landmark size={16} color={currentInterface === 'TREASURER' ? '#10b981' : 'currentColor'} />
              <span>{t('roleTreasurer')}</span>
            </button>
          )}

          {!isPlatformAdmin && (
            <button
              id="nav-member"
              className={`nav-tab ${currentInterface === 'MEMBER' ? 'active' : ''}`}
              onClick={() => setCurrentInterface('MEMBER')}
              title={t('roleMember')}
            >
              <UserCheck size={16} color={currentInterface === 'MEMBER' ? '#10b981' : 'currentColor'} />
              <span>{t('roleMember')}</span>
            </button>
          )}
        </div>

        {/* Right side controls: Group Selector, Language Toggle, User & Logout */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* Active Group Selector */}
          {groupRoles.length > 0 && currentInterface !== 'SUPER_ADMIN' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <select
                id="active-group-select"
                className="form-select"
                style={{ padding: '0.45rem 0.85rem', fontSize: '0.825rem', width: 'auto', minWidth: '180px' }}
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

          {/* Language Toggle Button */}
          <button
            id="lang-toggle-btn"
            onClick={toggleLanguage}
            className="btn btn-secondary"
            style={{ padding: '0.45rem 0.85rem', fontSize: '0.825rem' }}
            title="Switch Language / ቋንቋ ቀይር"
          >
            <Globe size={15} color="#f59e0b" />
            <span style={{ fontWeight: 700 }}>{language === 'en' ? 'አማርኛ' : 'English'}</span>
          </button>

          {/* User badge and logout */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', paddingLeft: '0.5rem', borderLeft: '1px solid var(--border-color)' }}>
            <div style={{ textAlign: 'right', display: 'none', md: 'block' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ffffff' }}>
                {user.full_name}
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                {user.email}
              </div>
            </div>

            <button
              id="logout-btn"
              onClick={logout}
              className="btn btn-danger"
              style={{ padding: '0.45rem 0.75rem', fontSize: '0.825rem' }}
              title={t('logout')}
            >
              <LogOut size={15} />
            </button>
          </div>

        </div>

      </div>
    </header>
  );
}
