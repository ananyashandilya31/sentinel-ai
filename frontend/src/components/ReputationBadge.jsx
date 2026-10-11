import React from 'react';

const REPUTATION_CONFIG = {
  MALICIOUS: {
    label: 'MALICIOUS',
    colorClass: 'badge-severity-critical',
    bg: '#f85149',
    text: '#ffffff',
  },
  SUSPICIOUS: {
    label: 'SUSPICIOUS',
    colorClass: 'badge-severity-high',
    bg: '#d29922',
    text: '#ffffff',
  },
  CLEAN: {
    label: 'CLEAN',
    colorClass: 'badge-severity-low',
    bg: '#238636',
    text: '#ffffff',
  },
  UNKNOWN: {
    label: 'UNKNOWN',
    colorClass: 'badge-severity-medium',
    bg: '#8b949e',
    text: '#ffffff',
  },
};

export default function ReputationBadge({ reputation }) {
  const repKey = (reputation || 'UNKNOWN').toUpperCase();
  const config = REPUTATION_CONFIG[repKey] || REPUTATION_CONFIG.UNKNOWN;

  return (
    <span
      className={`badge-severity ${config.colorClass}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        fontWeight: 'bold',
        fontSize: '11px',
        letterSpacing: '0.5px',
      }}
    >
      <span
        style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: config.bg,
        }}
      />
      {config.label}
    </span>
  );
}
