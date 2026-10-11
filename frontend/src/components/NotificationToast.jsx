import React, { useEffect } from 'react';
import { AlertOctagon, X } from 'lucide-react';
import SeverityBadge from './SeverityBadge';

/**
 * NotificationToast — stacked live-alert notifications.
 *
 * Rendered at the top-right of the SOC console whenever the
 * WebSocket stream pushes a NEW_INCIDENT event. Auto-dismisses
 * after `autoDismissMs` (default 8s); CRITICAL alerts persist
 * until the analyst acknowledges them.
 */
const TOAST_COLORS = {
  CRITICAL: 'var(--accent-red)',
  HIGH: 'var(--accent-amber)',
  MEDIUM: 'var(--accent-purple)',
  LOW: 'var(--accent-cyan)',
};

function Toast({ toast, onDismiss }) {
  const { incident } = toast;
  const color = TOAST_COLORS[incident?.severity] || 'var(--accent-cyan)';

  useEffect(() => {
    if (toast.incident?.severity === 'CRITICAL') return; // critical persists
    const timer = setTimeout(() => onDismiss(toast.id), 8000);
    return () => clearTimeout(timer);
  }, [toast, onDismiss]);

  return (
    <div
      className="toast-notification"
      style={{ borderLeft: `3px solid ${color}` }}
      role="alert"
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
        <AlertOctagon size={14} color={color} />
        <span style={{ fontSize: '0.7rem', fontWeight: 700, letterSpacing: '0.06em', color }}>
          LIVE ALERT
        </span>
        <SeverityBadge severity={incident?.severity} />
        <button
          className="toast-close"
          onClick={() => onDismiss(toast.id)}
          aria-label="Dismiss"
        >
          <X size={13} />
        </button>
      </div>
      <div className="toast-title">{incident?.title || 'Unknown incident'}</div>
      <div className="toast-meta">
        {incident?.type?.replace('_', ' ')}
        {incident?.evidence_count !== undefined && ` · ${incident.evidence_count} evidence logs`}
      </div>
    </div>
  );
}

export default function NotificationToast({ toasts, onDismiss }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="toast-container">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
