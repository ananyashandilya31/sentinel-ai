import React from 'react';

const EVENT_STYLES = {
  LOGIN_FAILED: {
    label: 'LOGIN FAILED',
    className: 'badge-event-failed',
  },
  LOGIN_SUCCESS: {
    label: 'LOGIN SUCCESS',
    className: 'badge-event-success',
  },
  DATA_TRANSFER: {
    label: 'DATA TRANSFER',
    className: 'badge-event-transfer',
  },
  PORT_CONNECT: {
    label: 'PORT CONNECT',
    className: 'badge-event-port',
  },
  PRIVILEGE_CHANGE: {
    label: 'PRIVILEGE CHANGE',
    className: 'badge-event-privilege',
  },
};

export default function EventTypeBadge({ eventType }) {
  const config = EVENT_STYLES[eventType] || {
    label: eventType || 'UNKNOWN',
    className: 'badge-event-default',
  };

  return (
    <span className={`badge-event ${config.className}`}>
      {config.label}
    </span>
  );
}
