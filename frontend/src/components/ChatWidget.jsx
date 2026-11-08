import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, X, Send, Minimize2, User, Shield, Users } from 'lucide-react';
import { api } from '../services/api';
import './ChatWidget.css';

export function ChatWidget({ currentUser }) {
  const [isOpen, setIsOpen] = useState(false);
  const [contactsData, setContactsData] = useState({
    current_user_role: '',
    total_unread: 0,
    contacts: [],
    super_admins: [],
    group_members: []
  });
  const [selectedRecipientId, setSelectedRecipientId] = useState('');
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState('');

  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom();
    }
  }, [messages]);

  // Load contacts list
  const loadContacts = async () => {
    try {
      const data = await api.getChatContacts();
      setContactsData(data);

      // Auto-select initial recipient if none selected
      if (!selectedRecipientId) {
        if (data.current_user_role === 'ORGANIZER') {
          if (data.super_admins && data.super_admins.length > 0) {
            setSelectedRecipientId(data.super_admins[0].id);
          } else if (data.group_members && data.group_members.length > 0) {
            setSelectedRecipientId(data.group_members[0].id);
          }
        } else if (data.contacts && data.contacts.length > 0) {
          setSelectedRecipientId(data.contacts[0].id);
        }
      }
    } catch (err) {
      console.error('Failed to load chat contacts:', err);
    }
  };

  // Load messages for currently selected recipient
  const loadMessages = async (recipientId) => {
    if (!recipientId) return;
    try {
      setLoadingMessages(true);
      setChatError('');
      const res = await api.getChatMessages(recipientId);
      setMessages(res.messages || []);
    } catch (err) {
      console.error('Failed to load chat messages:', err);
      setChatError(err.message || 'Could not load messages.');
    } finally {
      setLoadingMessages(false);
    }
  };

  // Poll contacts when closed (every 25s) or opened (every 4s)
  useEffect(() => {
    loadContacts();
    const interval = setInterval(() => {
      loadContacts();
    }, isOpen ? 4000 : 25000);
    return () => clearInterval(interval);
  }, [isOpen]);

  // When selectedRecipientId changes or chat opens, load messages
  useEffect(() => {
    if (isOpen && selectedRecipientId) {
      loadMessages(selectedRecipientId);
    }
  }, [isOpen, selectedRecipientId]);

  // Send a message
  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || !selectedRecipientId || sending) return;

    const text = inputText.trim();
    setInputText('');
    setSending(true);

    try {
      const activeContact = contactsData.contacts?.find(c => c.id === selectedRecipientId) ||
        contactsData.group_members?.find(c => c.id === selectedRecipientId) ||
        contactsData.super_admins?.find(c => c.id === selectedRecipientId);

      const groupId = activeContact?.group_id || null;
      const newMsg = await api.sendChatMessage(selectedRecipientId, text, groupId);
      setMessages(prev => [...prev, newMsg]);
      // Refresh contacts to update last_message
      loadContacts();
    } catch (err) {
      console.error('Failed to send message:', err);
      setChatError(err.message || 'Failed to send message.');
    } finally {
      setSending(false);
    }
  };

  // Identify active contact details
  const activeRecipient =
    contactsData.super_admins?.find(c => c.id === selectedRecipientId) ||
    contactsData.group_members?.find(c => c.id === selectedRecipientId) ||
    contactsData.contacts?.find(c => c.id === selectedRecipientId);

  return (
    <>
      {/* Floating Chat Launcher Button */}
      {!isOpen && (
        <button
          type="button"
          className="equb-chat-launcher"
          onClick={() => setIsOpen(true)}
          title="Open Equb Chat"
        >
          <MessageSquare size={18} />
          <span>Chat</span>
          {contactsData.total_unread > 0 && (
            <span className="equb-chat-badge">{contactsData.total_unread}</span>
          )}
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="equb-chat-window">
          {/* Header */}
          <div className="equb-chat-header">
            <div className="equb-chat-title-wrap">
              <MessageSquare size={18} color="#60a5fa" />
              <h4 className="equb-chat-title">Equb Chat</h4>
            </div>
            <div className="equb-chat-header-actions">
              <button
                type="button"
                className="equb-chat-header-btn"
                onClick={() => setIsOpen(false)}
                title="Minimize chat"
              >
                <Minimize2 size={16} />
              </button>
              <button
                type="button"
                className="equb-chat-header-btn"
                onClick={() => setIsOpen(false)}
                title="Close chat"
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Recipient Dropdown Selector */}
          <div className="equb-chat-selector-bar">
            {/* ORGANIZER VIEW: Dropdown switching between Super Admin and Members/Treasurers */}
            {contactsData.current_user_role === 'ORGANIZER' && (
              <>
                <label className="equb-chat-selector-label">Chat With:</label>
                <select
                  className="equb-chat-select"
                  value={selectedRecipientId}
                  onChange={(e) => setSelectedRecipientId(e.target.value)}
                >
                  <optgroup label="🛡️ Platform Super Admin">
                    {contactsData.super_admins?.map(sa => (
                      <option key={sa.id} value={sa.id}>
                        🛡️ {sa.full_name} {sa.unread_count > 0 ? `(${sa.unread_count} new)` : ''}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="👥 Group Members & Treasurers">
                    {contactsData.group_members?.map(gm => (
                      <option key={`${gm.id}-${gm.group_id}`} value={gm.id}>
                        {gm.role === 'TREASURER' ? '💰' : '👤'} {gm.full_name} — {gm.role_label} ({gm.group_name}) {gm.unread_count > 0 ? `(${gm.unread_count} new)` : ''}
                      </option>
                    ))}
                  </optgroup>
                </select>
              </>
            )}

            {/* SUPER ADMIN VIEW: Dropdown selecting Organizers */}
            {contactsData.current_user_role === 'SUPER_ADMIN' && (
              <>
                <label className="equb-chat-selector-label">Select Organizer:</label>
                <select
                  className="equb-chat-select"
                  value={selectedRecipientId}
                  onChange={(e) => setSelectedRecipientId(e.target.value)}
                >
                  {contactsData.contacts?.map(org => (
                    <option key={org.id} value={org.id}>
                      👤 {org.full_name} ({org.group_name || org.email}) {org.unread_count > 0 ? `(${org.unread_count} new)` : ''}
                    </option>
                  ))}
                  {(!contactsData.contacts || contactsData.contacts.length === 0) && (
                    <option value="" disabled>No active organizers available</option>
                  )}
                </select>
              </>
            )}

            {/* MEMBER OR TREASURER VIEW: Direct Chat with Group Organizer */}
            {(contactsData.current_user_role === 'MEMBER' || contactsData.current_user_role === 'TREASURER') && (
              <>
                {contactsData.contacts?.length > 1 ? (
                  <>
                    <label className="equb-chat-selector-label">Group Organizer:</label>
                    <select
                      className="equb-chat-select"
                      value={selectedRecipientId}
                      onChange={(e) => setSelectedRecipientId(e.target.value)}
                    >
                      {contactsData.contacts.map(c => (
                        <option key={c.id} value={c.id}>
                          👤 {c.full_name} ({c.group_name})
                        </option>
                      ))}
                    </select>
                  </>
                ) : (
                  <div style={{ fontSize: '0.8rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <Users size={14} />
                    <span>Organizer: <strong>{activeRecipient?.full_name || 'Group Organizer'}</strong></span>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Active Partner Info Strip */}
          {activeRecipient && (
            <div className="equb-chat-partner-strip">
              <span className="equb-chat-partner-name">
                {activeRecipient.full_name}
              </span>
              <span className="equb-chat-partner-role-tag">
                {activeRecipient.role_label || activeRecipient.role}
              </span>
            </div>
          )}

          {/* Messages Area */}
          <div className="equb-chat-messages">
            {chatError && (
              <div style={{ padding: '0.5rem', background: '#fee2e2', color: '#dc2626', borderRadius: '0.375rem', fontSize: '0.78rem' }}>
                {chatError}
              </div>
            )}

            {loadingMessages && messages.length === 0 && (
              <div className="equb-chat-empty-state">Loading messages...</div>
            )}

            {!loadingMessages && messages.length === 0 && (
              <div className="equb-chat-empty-state">
                <MessageSquare size={32} />
                <p>No messages yet.</p>
                <span style={{ fontSize: '0.75rem' }}>Start the conversation below!</span>
              </div>
            )}

            {messages.map((msg) => {
              const isSent = msg.sender === currentUser?.id || msg.sender_email === currentUser?.email;
              const formattedTime = new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

              return (
                <div key={msg.id} className={`equb-message-row ${isSent ? 'sent' : 'received'}`}>
                  <div className="equb-message-bubble">
                    {msg.message}
                  </div>
                  <div className="equb-message-meta">
                    {!isSent && <span>{msg.sender_name || 'Sender'} • </span>}
                    {formattedTime}
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <form className="equb-chat-input-bar" onSubmit={handleSendMessage}>
            <input
              type="text"
              className="equb-chat-input"
              placeholder={selectedRecipientId ? "Type a message..." : "Select recipient to chat"}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={!selectedRecipientId || sending}
            />
            <button
              type="submit"
              className="equb-chat-send-btn"
              disabled={!selectedRecipientId || !inputText.trim() || sending}
              title="Send message"
            >
              <Send size={15} />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
export default ChatWidget;
