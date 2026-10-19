import React from 'react';
import { Server, Database, Activity, RefreshCw, Terminal } from 'lucide-react';

export default function HealthPage({
  healthData,
  loading,
  latency,
  errorMsg,
  lastChecked,
  autoRefresh,
  setAutoRefresh,
  onCheckHealth,
}) {
  const isApiOnline = !!healthData;
  const isDbConnected = healthData?.database?.status === 'connected';

  return (
    <div>
      <div className="phase-banner">
        <div>
          <div className="phase-title">System Health</div>
          <div className="phase-description">
            FastAPI server health, database connection pool diagnostic, and network latency telemetry.
          </div>
        </div>
        <button className="action-btn" onClick={onCheckHealth} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'pulse' : ''} />
          {loading ? 'Checking...' : 'Ping Health'}
        </button>
      </div>

      {/* Telemetry / Status Cards Grid */}
      <div className="grid-cards">
        {/* Card 1: Backend API Service */}
        <div className="soc-card">
          <div className="card-header">
            <span className="card-title">
              <Server size={16} /> API Server
            </span>
            <span className={`badge ${isApiOnline ? 'badge-connected' : 'badge-error'}`}>
              {isApiOnline ? 'ONLINE' : 'UNREACHABLE'}
            </span>
          </div>
          <div className="metric-value">
            {isApiOnline ? 'FastAPI 0.110+' : 'Offline'}
          </div>
          <div className="metric-sub">
            {isApiOnline
              ? `Env: ${healthData?.environment} | v${healthData?.version}`
              : errorMsg || 'Check if uvicorn is running on port 8000'}
          </div>
        </div>

        {/* Card 2: Database Connection */}
        <div className="soc-card">
          <div className="card-header">
            <span className="card-title">
              <Database size={16} /> PostgreSQL Engine
            </span>
            <span className={`badge ${isDbConnected ? 'badge-connected' : 'badge-disconnected'}`}>
              {isDbConnected ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>
          <div className="metric-value">
            {healthData?.database?.engine?.toUpperCase() || 'POSTGRESQL'}
          </div>
          <div className="metric-sub">
            {isDbConnected
              ? 'Connection pool verified (SELECT 1 ping ok)'
              : healthData?.database?.error
              ? `Notice: ${healthData.database.error.slice(0, 45)}...`
              : 'Run docker-compose up or start PostgreSQL service'}
          </div>
        </div>

        {/* Card 3: Network Latency */}
        <div className="soc-card">
          <div className="card-header">
            <span className="card-title">
              <Activity size={16} /> API Latency
            </span>
            <span className="badge badge-connected">
              {latency !== null ? `${latency} ms` : '--'}
            </span>
          </div>
          <div className="metric-value">
            {latency !== null ? `${latency} ms` : '--'}
          </div>
          <div className="metric-sub">
            Last checked: {lastChecked || 'Just now'} (Auto-refresh: {autoRefresh ? '10s' : 'Off'})
          </div>
        </div>
      </div>

      {/* Diagnostic Inspector */}
      <div className="soc-details">
        <div className="details-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600 }}>
            <Terminal size={18} color="#38bdf8" />
            <span>Diagnostic Health Payload (`GET /api/v1/health`)</span>
          </div>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (10s)
          </label>
        </div>

        <pre className="json-inspector">
          {healthData
            ? JSON.stringify(healthData, null, 2)
            : JSON.stringify({ error: errorMsg, tip: 'Ensure backend is running at http://localhost:8000' }, null, 2)}
        </pre>
      </div>
    </div>
  );
}
