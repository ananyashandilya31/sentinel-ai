import React from 'react';

/**
 * AnomalyScoreBadge — visualises an Isolation Forest anomaly score [0, 1].
 *
 * Colour bands:
 *   Green   ≤ 0.40   → LOW risk
 *   Amber   ≤ 0.65   → MEDIUM risk
 *   Orange  ≤ 0.80   → HIGH risk
 *   Red     > 0.80   → CRITICAL
 */
export default function AnomalyScoreBadge({ score }) {
  const pct = Math.round((score || 0) * 100);

  let label, colorClass;
  if (pct <= 40) {
    label = 'LOW';
    colorClass = 'badge-low';
  } else if (pct <= 65) {
    label = 'MEDIUM';
    colorClass = 'badge-medium';
  } else if (pct <= 80) {
    label = 'HIGH';
    colorClass = 'badge-high';
  } else {
    label = 'CRITICAL';
    colorClass = 'badge-critical';
  }

  return (
    <span className={`severity-badge ${colorClass}`} title={`Anomaly score: ${score}`}>
      {pct}% · {label}
    </span>
  );
}
