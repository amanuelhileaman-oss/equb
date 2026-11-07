import React, { useState, useEffect } from 'react';
import { CheckCircle2, AlertTriangle, ArrowLeft, ShieldCheck, Smartphone, CreditCard, Building2, Copy, Check } from 'lucide-react';

export function ChapaSandboxCheckout() {
  const [params, setParams] = useState({
    tx_ref: '',
    amount: '0.00',
    currency: 'ETB',
    email: '',
    first_name: '',
    last_name: '',
    title: 'Digital Equb Payment',
    description: '',
    return_url: '',
    reason: ''
  });

  const [activeTab, setActiveTab] = useState('telebirr');
  const [phoneNumber, setPhoneNumber] = useState('0911234567');
  const [cardNumber, setCardNumber] = useState('4111 2222 3333 4444');
  const [cardExpiry, setCardExpiry] = useState('12/28');
  const [cardCvv, setCardCvv] = useState('123');
  const [copied, setCopied] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    setParams({
      tx_ref: urlParams.get('tx_ref') || `MOCK-${Date.now()}`,
      amount: urlParams.get('amount') || '600.00',
      currency: urlParams.get('currency') || 'ETB',
      email: urlParams.get('email') || 'organizer@digitalequb.et',
      first_name: urlParams.get('first_name') || 'Equb',
      last_name: urlParams.get('last_name') || 'User',
      title: urlParams.get('title') || 'Digital Equb Ethiopia Subscription Rent',
      description: urlParams.get('description') || 'Monthly SaaS Platform Organizer Rent (Chapa)',
      return_url: urlParams.get('return_url') || '/',
      reason: urlParams.get('reason') || ''
    });
  }, []);

  const handleCopyRef = () => {
    if (params.tx_ref) {
      navigator.clipboard.writeText(params.tx_ref);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSimulatePayment = (success = true) => {
    setIsProcessing(true);
    setStatusMessage(success ? 'Authorizing test payment with Chapa Gateway...' : 'Simulating failed authorization...');

    setTimeout(() => {
      setStatusMessage(success ? 'Payment Approved! Redirecting back to Digital Equb...' : 'Payment cancelled or declined.');
      setTimeout(() => {
        const rawReturn = params.return_url || '/';
        const url = new URL(rawReturn, window.location.origin);
        url.searchParams.set('tx_ref', params.tx_ref);
        url.searchParams.set('status', success ? 'success' : 'failed');
        window.location.href = url.toString();
      }, 800);
    }, 1200);
  };

  const formattedAmount = Number(params.amount || 0).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: '#0c1322',
      color: '#f8fafc',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1.5rem'
    }}>
      {/* Container */}
      <div style={{
        width: '100%',
        maxWidth: '520px',
        backgroundColor: '#131e33',
        borderRadius: '16px',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.08)',
        overflow: 'hidden'
      }}>
        {/* Header Branding */}
        <div style={{
          background: 'linear-gradient(135deg, #00C48C 0%, #008f65 100%)',
          padding: '1.5rem 1.75rem',
          color: '#ffffff'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <div style={{
                background: '#ffffff',
                color: '#008f65',
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 900,
                fontSize: '1.1rem'
              }}>
                C
              </div>
              <span style={{ fontWeight: 800, fontSize: '1.25rem', letterSpacing: '-0.02em' }}>chapa</span>
            </div>
            <span style={{
              background: 'rgba(0, 0, 0, 0.25)',
              padding: '0.25rem 0.65rem',
              borderRadius: '20px',
              fontSize: '0.72rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.05em'
            }}>
              Sandbox Test Mode
            </span>
          </div>

          <div style={{ fontSize: '0.85rem', opacity: 0.9 }}>Digital Equb Ethiopia Secure Checkout</div>
          <div style={{ fontSize: '1.9rem', fontWeight: 800, marginTop: '0.35rem', letterSpacing: '-0.02em' }}>
            {params.currency} {formattedAmount}
          </div>
        </div>

        {/* Informative Sandbox Banner */}
        {params.reason && (
          <div style={{
            background: 'rgba(234, 179, 8, 0.12)',
            borderLeft: '4px solid #eab308',
            padding: '0.85rem 1.25rem',
            fontSize: '0.82rem',
            color: '#fef08a',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '0.65rem'
          }}>
            <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: '2px', color: '#eab308' }} />
            <div>
              <div style={{ fontWeight: 700, marginBottom: '2px' }}>Chapa API Live Status: Test Fallback</div>
              <div style={{ opacity: 0.9, lineHeight: 1.4 }}>
                {params.reason.includes('401')
                  ? 'Your Chapa Secret Key is unverified/inactive on Chapa. Local Sandbox Mode is active so you can test complete end-to-end payments smoothly.'
                  : params.reason
                }
              </div>
            </div>
          </div>
        )}

        <div style={{ padding: '1.5rem 1.75rem' }}>
          {/* Transaction Metadata Card */}
          <div style={{
            background: 'rgba(255, 255, 255, 0.03)',
            borderRadius: '10px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            padding: '1rem',
            marginBottom: '1.25rem',
            fontSize: '0.85rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ color: '#94a3b8' }}>Payment Purpose</span>
              <span style={{ fontWeight: 600, color: '#f1f5f9' }}>{params.title}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ color: '#94a3b8' }}>Transaction Ref</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <code style={{
                  background: 'rgba(0, 196, 140, 0.1)',
                  color: '#00C48C',
                  padding: '0.2rem 0.45rem',
                  borderRadius: '4px',
                  fontSize: '0.78rem',
                  fontFamily: 'monospace'
                }}>
                  {params.tx_ref}
                </code>
                <button
                  type="button"
                  onClick={handleCopyRef}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                    padding: '2px',
                    display: 'flex'
                  }}
                  title="Copy reference"
                >
                  {copied ? <Check size={14} color="#00C48C" /> : <Copy size={14} />}
                </button>
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#94a3b8' }}>Payer</span>
              <span style={{ color: '#e2e8f0' }}>{params.first_name} {params.last_name} ({params.email})</span>
            </div>
          </div>

          {/* Payment Method Selectors */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem', fontWeight: 600 }}>
              SELECT TEST PAYMENT CHANNEL
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
              <button
                type="button"
                onClick={() => setActiveTab('telebirr')}
                style={{
                  background: activeTab === 'telebirr' ? 'rgba(0, 196, 140, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                  border: `1.5px solid ${activeTab === 'telebirr' ? '#00C48C' : 'rgba(255, 255, 255, 0.1)'}`,
                  borderRadius: '10px',
                  padding: '0.75rem',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem',
                  fontSize: '0.85rem',
                  fontWeight: activeTab === 'telebirr' ? 700 : 500
                }}
              >
                <Smartphone size={18} color={activeTab === 'telebirr' ? '#00C48C' : '#94a3b8'} />
                <span>Telebirr</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('cbe')}
                style={{
                  background: activeTab === 'cbe' ? 'rgba(0, 196, 140, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                  border: `1.5px solid ${activeTab === 'cbe' ? '#00C48C' : 'rgba(255, 255, 255, 0.1)'}`,
                  borderRadius: '10px',
                  padding: '0.75rem',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem',
                  fontSize: '0.85rem',
                  fontWeight: activeTab === 'cbe' ? 700 : 500
                }}
              >
                <Building2 size={18} color={activeTab === 'cbe' ? '#00C48C' : '#94a3b8'} />
                <span>CBE Birr</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('card')}
                style={{
                  background: activeTab === 'card' ? 'rgba(0, 196, 140, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                  border: `1.5px solid ${activeTab === 'card' ? '#00C48C' : 'rgba(255, 255, 255, 0.1)'}`,
                  borderRadius: '10px',
                  padding: '0.75rem',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem',
                  fontSize: '0.85rem',
                  fontWeight: activeTab === 'card' ? 700 : 500
                }}
              >
                <CreditCard size={18} color={activeTab === 'card' ? '#00C48C' : '#94a3b8'} />
                <span>Bank Card</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('awash')}
                style={{
                  background: activeTab === 'awash' ? 'rgba(0, 196, 140, 0.15)' : 'rgba(255, 255, 255, 0.04)',
                  border: `1.5px solid ${activeTab === 'awash' ? '#00C48C' : 'rgba(255, 255, 255, 0.1)'}`,
                  borderRadius: '10px',
                  padding: '0.75rem',
                  color: '#f8fafc',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem',
                  fontSize: '0.85rem',
                  fontWeight: activeTab === 'awash' ? 700 : 500
                }}
              >
                <Building2 size={18} color={activeTab === 'awash' ? '#00C48C' : '#94a3b8'} />
                <span>Awash / BOA</span>
              </button>
            </div>
          </div>

          {/* Tab Input Fields */}
          <div style={{
            background: 'rgba(0, 0, 0, 0.25)',
            borderRadius: '10px',
            padding: '1.25rem',
            marginBottom: '1.5rem',
            border: '1px solid rgba(255, 255, 255, 0.06)'
          }}>
            {activeTab === 'telebirr' && (
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.4rem' }}>
                  Telebirr Phone Number
                </label>
                <input
                  type="text"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="09XXXXXXXX"
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.85rem',
                    background: '#0d1527',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    color: '#ffffff',
                    fontSize: '0.95rem'
                  }}
                />
                <div style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '0.4rem' }}>
                  Simulation mode: Any Ethiopian phone number will authorize instantly.
                </div>
              </div>
            )}

            {activeTab === 'cbe' && (
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.4rem' }}>
                  CBE Birr Account / Phone Number
                </label>
                <input
                  type="text"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="09XXXXXXXX or 1000XXXXXXXX"
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.85rem',
                    background: '#0d1527',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    color: '#ffffff',
                    fontSize: '0.95rem'
                  }}
                />
                <div style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '0.4rem' }}>
                  Simulation mode: Commercial Bank of Ethiopia sandbox verification.
                </div>
              </div>
            )}

            {activeTab === 'card' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                    Card Number (Visa / Mastercard)
                  </label>
                  <input
                    type="text"
                    value={cardNumber}
                    onChange={(e) => setCardNumber(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.65rem 0.85rem',
                      background: '#0d1527',
                      border: '1px solid rgba(255, 255, 255, 0.15)',
                      borderRadius: '8px',
                      color: '#ffffff',
                      fontSize: '0.95rem'
                    }}
                  />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                      Expiry
                    </label>
                    <input
                      type="text"
                      value={cardExpiry}
                      onChange={(e) => setCardExpiry(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.65rem 0.85rem',
                        background: '#0d1527',
                        border: '1px solid rgba(255, 255, 255, 0.15)',
                        borderRadius: '8px',
                        color: '#ffffff',
                        fontSize: '0.95rem'
                      }}
                    />
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.35rem' }}>
                      CVV
                    </label>
                    <input
                      type="text"
                      value={cardCvv}
                      onChange={(e) => setCardCvv(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '0.65rem 0.85rem',
                        background: '#0d1527',
                        border: '1px solid rgba(255, 255, 255, 0.15)',
                        borderRadius: '8px',
                        color: '#ffffff',
                        fontSize: '0.95rem'
                      }}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'awash' && (
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.4rem' }}>
                  Bank Account Number
                </label>
                <input
                  type="text"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="013XXXXXXXXXX"
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.85rem',
                    background: '#0d1527',
                    border: '1px solid rgba(255, 255, 255, 0.15)',
                    borderRadius: '8px',
                    color: '#ffffff',
                    fontSize: '0.95rem'
                  }}
                />
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <button
              type="button"
              disabled={isProcessing}
              onClick={() => handleSimulatePayment(true)}
              style={{
                width: '100%',
                background: isProcessing ? '#059669' : '#00C48C',
                color: '#ffffff',
                border: 'none',
                borderRadius: '10px',
                padding: '0.95rem',
                fontSize: '1rem',
                fontWeight: 700,
                cursor: isProcessing ? 'wait' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.6rem',
                transition: 'all 0.2s ease',
                boxShadow: '0 4px 15px rgba(0, 196, 140, 0.3)'
              }}
            >
              {isProcessing ? (
                <>
                  <div style={{
                    width: '18px',
                    height: '18px',
                    border: '2px solid #ffffff',
                    borderTopColor: 'transparent',
                    borderRadius: '50%',
                    animation: 'spin 0.6s linear infinite'
                  }} />
                  <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                  <span>{statusMessage}</span>
                </>
              ) : (
                <>
                  <CheckCircle2 size={20} />
                  <span>Authorize & Pay {params.currency} {formattedAmount} (Test Mode)</span>
                </>
              )}
            </button>

            <button
              type="button"
              disabled={isProcessing}
              onClick={() => handleSimulatePayment(false)}
              style={{
                width: '100%',
                background: 'transparent',
                color: '#ef4444',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '10px',
                padding: '0.65rem',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: isProcessing ? 'wait' : 'pointer'
              }}
            >
              Simulate Cancelled / Failed Payment
            </button>

            <a
              href={params.return_url || '/'}
              style={{
                textAlign: 'center',
                fontSize: '0.82rem',
                color: '#64748b',
                textDecoration: 'none',
                marginTop: '0.25rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.35rem'
              }}
            >
              <ArrowLeft size={14} />
              <span>Back to Digital Equb</span>
            </a>
          </div>

          <div style={{
            marginTop: '1.5rem',
            textAlign: 'center',
            fontSize: '0.74rem',
            color: '#64748b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.4rem'
          }}>
            <ShieldCheck size={14} color="#00C48C" />
            <span>256-bit Encrypted Chapa Payment Gateway • Sandbox Environment</span>
          </div>
        </div>
      </div>
    </div>
  );
}

