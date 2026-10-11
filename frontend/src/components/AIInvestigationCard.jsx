import React from 'react';
import {
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  AlertOctagon,
  RefreshCw,
  Terminal,
  BookmarkCheck,
} from 'lucide-react';
import SeverityBadge from './SeverityBadge';

export default function AIInvestigationCard({
  investigation,
  onReinvestigate,
  loading = false,
}) {
  if (!investigation) return null;

  const confidencePct = Math.round((investigation.confidence_score || 0.9) * 100);

  return (
    <div
      style={{
        backgroundColor: '#161b22',
        border: '1px solid #388bfd40',
        borderRadius: '8px',
        padding: '1.25rem',
        marginBottom: '1.5rem',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)',
      }}
    >
      {/* ── Card Header ─────────────────────────────────────────────────────── */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '0.75rem',
          marginBottom: '1rem',
          borderBottom: '1px solid #30363d',
          paddingBottom: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div
            style={{
              padding: '6px',
              borderRadius: '6px',
              backgroundColor: 'rgba(56, 189, 248, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Sparkles size={18} color="#38bdf8" />
          </div>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: '#f0f6fc', margin: 0 }}>
              AI Incident Investigation
            </h3>
            <span style={{ fontSize: '11px', color: '#8b949e' }}>
              Synthesized by {investigation.model_used}
            </span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: '12px',
              backgroundColor: 'rgba(35, 134, 54, 0.2)',
              color: '#3fb950',
              border: '1px solid #238636',
            }}
          >
            {confidencePct}% Confidence
          </span>

          <SeverityBadge severity={investigation.severity} />

          {onReinvestigate && (
            <button
              className="action-btn"
              onClick={onReinvestigate}
              disabled={loading}
              title="Regenerate analysis bypassing cache"
              style={{
                fontSize: '11px',
                padding: '3px 8px',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <RefreshCw size={12} className={loading ? 'spin' : ''} />
              {loading ? 'Re-analyzing...' : 'Re-analyze'}
            </button>
          )}
        </div>
      </div>

      {/* ── Executive Summary ──────────────────────────────────────────────── */}
      <div
        style={{
          backgroundColor: '#0d1117',
          borderLeft: '4px solid #38bdf8',
          borderTop: '1px solid #30363d',
          borderRight: '1px solid #30363d',
          borderBottom: '1px solid #30363d',
          borderRadius: '4px',
          padding: '0.85rem 1rem',
          marginBottom: '1rem',
        }}
      >
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#38bdf8', textTransform: 'uppercase', marginBottom: '4px' }}>
          Incident Summary
        </div>
        <p style={{ fontSize: '13px', color: '#c9d1d9', lineHeight: '1.5', margin: 0 }}>
          {investigation.summary}
        </p>
      </div>

      {/* ── Evidence & Recommended Actions 2-Column Grid ───────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
        {/* Key Correlated Evidence */}
        <div
          style={{
            backgroundColor: '#0d1117',
            border: '1px solid #30363d',
            borderRadius: '6px',
            padding: '0.85rem',
          }}
        >
          <div
            style={{
              fontSize: '12px',
              fontWeight: 600,
              color: '#f0f6fc',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              marginBottom: '0.6rem',
            }}
          >
            <ShieldCheck size={14} color="#f85149" />
            Key Correlated Evidence
          </div>
          <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '12px', color: '#8b949e', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {investigation.evidence_points && investigation.evidence_points.length > 0 ? (
              investigation.evidence_points.map((point, idx) => (
                <li key={idx} style={{ color: '#c9d1d9', lineHeight: '1.4' }}>
                  {point}
                </li>
              ))
            ) : (
              <li style={{ color: '#8b949e' }}>No specific evidence points recorded.</li>
            )}
          </ul>
        </div>

        {/* Recommended Analyst Actions */}
        <div
          style={{
            backgroundColor: '#0d1117',
            border: '1px solid #30363d',
            borderRadius: '6px',
            padding: '0.85rem',
          }}
        >
          <div
            style={{
              fontSize: '12px',
              fontWeight: 600,
              color: '#f0f6fc',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              marginBottom: '0.6rem',
            }}
          >
            <CheckCircle2 size={14} color="#3fb950" />
            Recommended Investigation Actions
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {investigation.recommended_actions && investigation.recommended_actions.length > 0 ? (
              investigation.recommended_actions.map((act, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    fontSize: '12px',
                    color: '#c9d1d9',
                    lineHeight: '1.4',
                  }}
                >
                  <span
                    style={{
                      backgroundColor: 'rgba(56, 189, 248, 0.2)',
                      color: '#38bdf8',
                      fontSize: '10px',
                      fontWeight: 700,
                      padding: '1px 5px',
                      borderRadius: '3px',
                      marginTop: '2px',
                    }}
                  >
                    {idx + 1}
                  </span>
                  <span>{act}</span>
                </div>
              ))
            ) : (
              <span style={{ fontSize: '12px', color: '#8b949e' }}>No recommendations provided.</span>
            )}
          </div>
        </div>
      </div>

      {/* ── MITRE ATT&CK Matrix Mapping ────────────────────────────────────── */}
      {investigation.mitre_tactics && investigation.mitre_tactics.length > 0 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            flexWrap: 'wrap',
            paddingTop: '0.5rem',
            borderTop: '1px solid #30363d',
          }}
        >
          <span style={{ fontSize: '11px', fontWeight: 600, color: '#8b949e', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Terminal size={12} /> MITRE ATT&CK:
          </span>
          {investigation.mitre_tactics.map((tac, idx) => (
            <span
              key={idx}
              style={{
                fontSize: '11px',
                fontFamily: 'monospace',
                backgroundColor: 'rgba(163, 113, 247, 0.15)',
                color: '#d2a8ff',
                border: '1px solid rgba(163, 113, 247, 0.3)',
                padding: '2px 7px',
                borderRadius: '4px',
              }}
            >
              {tac}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
