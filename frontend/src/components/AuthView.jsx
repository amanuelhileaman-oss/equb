import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { HeaderControls } from './HeaderControls';
import { Lock, CheckCircle2, AlertCircle, Layers } from 'lucide-react';

export function AuthView() {
  const { login } = useAuth();
  const { t } = useLanguage();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // MFA 2-Factor Authentication state
  const [mfaRequired, setMfaRequired] = useState(false);
  const [mfaCode, setMfaCode] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    setLoading(true);

    try {
      if (mfaRequired) {
        const res = await login(email, password, mfaCode);
        if (res?.mfa_required) {
          setError('Invalid 6-digit MFA code. Please check your authenticator clock.');
        }
      } else {
        const res = await login(email, password);
        if (res?.mfa_required) {
          setMfaRequired(true);
        }
      }
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1.5rem',
      position: 'relative'
    }}>
      {/* Top right Theme & Language Controls */}
      <div style={{ position: 'absolute', top: '1.5rem', right: '1.5rem', zIndex: 50 }}>
        <HeaderControls />
      </div>

      <div className="glass-card" style={{ width: '100%', maxWidth: '440px', padding: '2.5rem' }}>
        {/* Brand header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            width: '56px',
            height: '56px',
            margin: '0 auto 1rem',
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #10b981 0%, #f59e0b 50%, #ef4444 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 25px rgba(16, 185, 129, 0.4)'
          }}>
            <Layers size={32} color="#ffffff" />
          </div>
          <h1 style={{ fontSize: '1.65rem', marginBottom: '0.35rem' }}>{t('brandName')}</h1>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
            {t('loginSubtitle')}
          </p>
        </div>

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '0.75rem 1rem',
            marginBottom: '1.25rem',
            color: '#f87171',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.875rem'
          }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div style={{
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: 'var(--radius-md)',
            padding: '0.75rem 1rem',
            marginBottom: '1.25rem',
            color: '#34d399',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.875rem'
          }}>
            <CheckCircle2 size={18} />
            <span>{successMsg}</span>
          </div>
        )}

        {mfaRequired ? (
          <form onSubmit={handleSubmit}>
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              <div style={{
                width: '52px',
                height: '52px',
                margin: '0 auto 0.75rem',
                borderRadius: '50%',
                backgroundColor: 'rgba(37, 99, 235, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 4px 12px rgba(37, 99, 235, 0.2)'
              }}>
                <Lock size={26} color="#2563eb" />
              </div>
              <h2 style={{ fontSize: '1.25rem', marginBottom: '0.25rem', color: 'var(--text-primary)' }}>Two-Factor Authentication</h2>
              <p style={{ fontSize: '0.825rem', color: 'var(--text-secondary)' }}>
                Enter the 6-digit verification code from your authenticator app for <strong>{email}</strong>
              </p>
            </div>

            <div className="form-group">
              <label className="form-label" style={{ textAlign: 'center', display: 'block', fontSize: '0.8rem', fontWeight: 600 }}>6-Digit TOTP Code</label>
              <input
                type="text"
                required
                maxLength="6"
                autoFocus
                className="form-input"
                style={{ fontSize: '1.4rem', textAlign: 'center', letterSpacing: '0.25em', fontWeight: 700 }}
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value.trim())}
                placeholder="123456"
              />
            </div>

            <button
              type="submit"
              disabled={loading || mfaCode.length !== 6}
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '0.75rem', padding: '0.85rem' }}
            >
              {loading ? 'Verifying...' : 'Verify & Sign In'}
            </button>

            <div style={{ textAlign: 'center', marginTop: '1.25rem' }}>
              <button
                type="button"
                onClick={() => { setMfaRequired(false); setMfaCode(''); setError(''); }}
                style={{ background: 'none', border: 'none', color: '#64748b', fontSize: '0.825rem', cursor: 'pointer', textDecoration: 'underline' }}
              >
                ← Back to standard login
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">{t('email')}</label>
              <input
                type="email"
                required
                className="form-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@digitalequb.et"
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t('password')}</label>
              <input
                type="password"
                required
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{ width: '100%', marginTop: '1rem', padding: '0.85rem' }}
            >
              {loading ? t('loading') : t('login')}
            </button>
          </form>
        )}

      </div>
    </div>
  );
}
