import React from 'react';

const STATUS_STYLES = {
  OPEN: {
    label: 'OPEN',
    className: 'badge-status-open',
  },
  INVESTIGATING: {
    label: 'INVESTIGATING',
    className: 'badge-status-investigating',
  },
  RESOLVED: {
    label: 'RESOLVED',
    className: 'badge-status-resolved',
  },
  FALSE_POSITIVE: {
    label: 'FALSE POSITIVE',
    className: 'badge-status-fp',
  },
};

export default function StatusBadge({ status }) {
  const config = STATUS_STYLES[status] || {
    label: status || 'UNKNOWN',
    className: 'badge-status-open',
  };

  return (
    <span className={`badge-status ${config.className}`}>
      {config.label}
    </span>
  );
}
