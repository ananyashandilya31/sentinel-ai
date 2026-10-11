import React from 'react';

const SEVERITY_STYLES = {
  CRITICAL: {
    label: 'CRITICAL',
    className: 'badge-severity-critical',
  },
  HIGH: {
    label: 'HIGH',
    className: 'badge-severity-high',
  },
  MEDIUM: {
    label: 'MEDIUM',
    className: 'badge-severity-medium',
  },
  LOW: {
    label: 'LOW',
    className: 'badge-severity-low',
  },
};

export default function SeverityBadge({ severity }) {
  const config = SEVERITY_STYLES[severity] || {
    label: severity || 'UNKNOWN',
    className: 'badge-severity-low',
  };

  return (
    <span className={`badge-severity ${config.className}`}>
      {config.label}
    </span>
  );
}
