import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield,
  Server,
  Database,
  Activity,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Terminal,
  Cpu,
} from 'lucide-react';
import { fetchHealthStatus } from './services/api';

export default function App() {
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [latency, setLatency] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastChecked, setLastChecked] = useState(null);

  const checkHealth = useCallback(async () => {
    setLoading(true);
    const result = await fetchHealthStatus();
    setLatency(result.latencyMs);

    if (result.success) {
      setHealthData(result.data);
      setErrorMsg(null);
    } else {
      setHealthData(null);
      setErrorMsg(result.error);
    }

    setLastChecked(new Date().toLocaleTimeString());
    setLoading(false);
  }, []);

  useEffect(() => {
    checkHealth();
    if (!autoRefresh) return;
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, [checkHealth, autoRefresh]);

  const isApiOnline = !!healthData;
  const isDbConnected = healthData?.database?.status === 'connected';

  // System overall health badge
  let systemStatusText = 'OFFLINE';
  let systemStatusClass = 'badge-error';
  let indicatorColor = 'var(--accent-red)';

  if (isApiOnline && isDbConnected) {
    systemStatusText = 'SYSTEM ACTIVE';
    systemStatusClass = 'badge-connected';
    indicatorColor = 'var(--accent-green)';
  } else if (isApiOnline && !isDbConnected) {
    systemStatusText = 'DB DISCONNECTED';
    systemStatusClass = 'badge-disconnected';
    indicatorColor = 'var(--accent-amber)';
  }

  return (
    <div className="soc-app">
      {/* Top SOC Navigation Bar */}
      <header className="soc-header">
        <div className="brand-container">
          <Shield size={26} color="#38bdf8" />
          <h1 className="brand-title">SENTINELAI</h1>
          <span className="brand-tag">SOC CORE v0.1</span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div
            className={`system-status-pill ${systemStatusClass}`}
            style={{ border: `1px solid ${indicatorColor}` }}
          >
            <div
              className="status-indicator pulse"
              style={{ backgroundColor: indicatorColor }}
            />
            {systemStatusText}
          </div>
        </div>
      </header>

      {/* Main SOC Viewport */}
      <main className="soc-content">
        <div className="phase-banner">
          <div>
            <div className="phase-title">Phase 1: Foundation Completed</div>
            <div className="phase-description">
              FastAPI backend, PostgreSQL connection pool, Alembic schema migrations, and React + Vite SOC dashboard.
            </div>
          </div>
          <button
            className="action-btn"
            onClick={checkHealth}
            disabled={loading}
          >
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
      </main>

      {/* Footer */}
      <footer className="soc-footer">
        SentinelAI SOC — AI-Powered Security Operations Center • Phase 1 Foundation Active
      </footer>
    </div>
  );
}
