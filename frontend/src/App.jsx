import React, { useState } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import { Sidebar } from './components/Sidebar';
import { AuthView } from './components/AuthView';
import { SuperAdminDashboard } from './interfaces/SuperAdminDashboard';
import { OrganizerDashboard } from './interfaces/OrganizerDashboard';
import { TreasurerDashboard } from './interfaces/TreasurerDashboard';
import { MemberInterface } from './interfaces/MemberInterface';
import { ChapaSandboxCheckout } from './components/ChapaSandboxCheckout';
import { Menu } from 'lucide-react';

function AppContent() {
  // If navigating to the Chapa Sandbox Hosted Checkout Portal
  if (window.location.pathname.startsWith('/sandbox/chapa-checkout')) {
    return <ChapaSandboxCheckout />;
  }

  const { user, loading, currentInterface } = useAuth();
  const { t } = useLanguage();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: '1rem'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          border: '3px solid rgba(16, 185, 129, 0.2)',
          borderTopColor: '#10b981',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite'
        }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Initializing Digital Equb Secure Platform...
        </div>
      </div>
    );
  }

  if (!user) {
    return <AuthView />;
  }

  const getPortalTitle = () => {
    switch (currentInterface) {
      case 'SUPER_ADMIN': return t('roleSuperAdmin');
      case 'ORGANIZER': return t('roleOrganizer');
      case 'TREASURER': return t('roleTreasurer');
      case 'MEMBER': return t('roleMember');
      default: return 'Portal';
    }
  };

  if (currentInterface === 'SUPER_ADMIN') {
    return <SuperAdminDashboard />;
  }

  if (currentInterface === 'ORGANIZER') {
    return <OrganizerDashboard />;
  }

  if (currentInterface === 'TREASURER') {
    return <TreasurerDashboard />;
  }

  if (currentInterface === 'MEMBER') {
    return <MemberInterface />;
  }

  return (
    <div className="app-layout">
      {/* Vertical Navigation Sidebar with Role Switcher Tabs */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main Content Area */}
      <div className="app-main-area">
        {/* Mobile Top Bar */}
        <header className="mobile-top-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="btn btn-secondary"
              style={{ padding: '0.45rem', borderRadius: 'var(--radius-sm)' }}
              aria-label="Open navigation menu"
            >
              <Menu size={20} />
            </button>
            <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#ffffff' }}>
              {getPortalTitle()}
            </div>
          </div>
          <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>MVP</span>
        </header>

        {/* Dynamic Dashboard View */}
        <main style={{ flex: 1 }}>
          {currentInterface === 'SUPER_ADMIN' && <SuperAdminDashboard />}
          {currentInterface === 'ORGANIZER' && <OrganizerDashboard />}
          {currentInterface === 'TREASURER' && <TreasurerDashboard />}
          {currentInterface === 'MEMBER' && <MemberInterface />}
        </main>

        <footer style={{
          borderTop: '1px solid var(--border-color)',
          padding: '1.5rem',
          textAlign: 'center',
          fontSize: '0.8rem',
          color: 'var(--text-muted)',
          background: 'rgba(8, 14, 26, 0.8)'
        }}>
          Digital Equb Ethiopia • Secure Multi-Tenant Equb Management SaaS MVP • Ethiopian Birr (ETB)
        </footer>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}
