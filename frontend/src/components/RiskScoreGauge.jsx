import React from 'react';

/**
 * RiskScoreGauge — Renders a numeric 0-100 risk score and mini progress bar.
 */
export default function RiskScoreGauge({ score = 0 }) {
  const numScore = Math.min(Math.max(Number(score) || 0, 0), 100);

  let barColor = '#238636'; // Green
  let label = 'Low Risk';

  if (numScore >= 75) {
    barColor = '#f85149'; // Red / Critical
    label = 'Critical Risk';
  } else if (numScore >= 50) {
    barColor = '#db6d28'; // Orange / High
    label = 'High Risk';
  } else if (numScore >= 25) {
    barColor = '#d29922'; // Yellow / Medium
    label = 'Moderate Risk';
  }

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', minWidth: '90px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
        <span style={{ fontWeight: 600, fontSize: '13px', color: barColor }}>
          {numScore} / 100
        </span>
      </div>
      <div
        style={{
          width: '100%',
          height: '6px',
          backgroundColor: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '3px',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: `${numScore}%`,
            height: '100%',
            backgroundColor: barColor,
            transition: 'width 0.3s ease',
          }}
        />
      </div>
    </div>
  );
}
