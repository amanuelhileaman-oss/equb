import React, { useState, useEffect, useRef } from 'react';
import { AlertCircle, CheckCircle2, Info, X, GripVertical } from 'lucide-react';
import './ToastNotification.css';

export function ToastNotification({ message, type = 'error', onClose, duration = 4000 }) {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [isLeaving, setIsLeaving] = useState(false);
  const dragStartRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (!duration || duration <= 0) return;
    const timer = setTimeout(() => {
      handleDismiss();
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, message]);

  const handleDismiss = () => {
    setIsLeaving(true);
    setTimeout(() => {
      if (onClose) onClose();
    }, 250);
  };

  // Mouse / Touch Drag handlers so the alert is movable!
  const handlePointerDown = (e) => {
    setIsDragging(true);
    dragStartRef.current = {
      x: e.clientX - position.x,
      y: e.clientY - position.y
    };
  };

  const handlePointerMove = (e) => {
    if (!isDragging) return;
    setPosition({
      x: e.clientX - dragStartRef.current.x,
      y: e.clientY - dragStartRef.current.y
    });
  };

  const handlePointerUp = () => {
    setIsDragging(false);
  };

  if (!message) return null;

  // Ensure message is short
  const shortMessage = typeof message === 'string' && message.length > 90
    ? `${message.slice(0, 87)}...`
    : message;

  return (
    <div className="toast-portal">
      <div
        className={`toast-item toast-${type} ${isLeaving ? 'toast-leaving' : ''}`}
        style={{
          transform: `translate(${position.x}px, ${position.y}px)`,
          transition: isDragging ? 'none' : 'transform 0.15s ease'
        }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
      >
        <div className="toast-content">
          <GripVertical size={14} style={{ opacity: 0.6, cursor: 'grab', flexShrink: 0 }} />
          {type === 'error' && <AlertCircle size={18} style={{ flexShrink: 0 }} />}
          {type === 'success' && <CheckCircle2 size={18} style={{ flexShrink: 0 }} />}
          {type === 'info' && <Info size={18} style={{ flexShrink: 0 }} />}
          <span className="toast-message" title={message}>{shortMessage}</span>
        </div>
        <button
          type="button"
          onClick={handleDismiss}
          className="toast-close-btn"
          aria-label="Close notification"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}

