import React from 'react';
import { Shield, Activity, FileText, AlertOctagon, BrainCircuit, ShieldAlert, LayoutDashboard } from 'lucide-react';

export default function Navbar({ currentTab, onSelectTab, systemStatus, openIncidentsCount = 0 }) {
  const { isApiOnline, isDbConnected } = systemStatus;

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
    <header className="soc-header">
      <div className="brand-container">
        <Shield size={26} color="#38bdf8" />
        <h1 className="brand-title">SENTINELAI</h1>
        <span className="brand-tag">SOC CORE v0.1</span>
      </div>

      {/* Navigation Tabs */}
      <nav className="nav-tabs">
        <button
          className={`nav-tab-btn ${currentTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => onSelectTab('dashboard')}
        >
          <LayoutDashboard size={16} />
          <span>Dashboard</span>
          <span className="live-dot" style={{ width: 6, height: 6 }} />
        </button>
        <button
          className={`nav-tab-btn ${currentTab === 'incidents' ? 'active' : ''}`}
          onClick={() => onSelectTab('incidents')}
        >
          <AlertOctagon size={16} />
          <span>Incidents</span>
          {openIncidentsCount > 0 && (
            <span className="nav-counter-pill">{openIncidentsCount}</span>
          )}
        </button>
        <button
          className={`nav-tab-btn ${currentTab === 'ml' ? 'active' : ''}`}
          onClick={() => onSelectTab('ml')}
        >
          <BrainCircuit size={16} />
          <span>ML Anomalies</span>
        </button>
        <button
          className={`nav-tab-btn ${currentTab === 'threat-intel' ? 'active' : ''}`}
          onClick={() => onSelectTab('threat-intel')}
        >
          <ShieldAlert size={16} />
          <span>Threat Intel</span>
        </button>
        <button
          className={`nav-tab-btn ${currentTab === 'events' ? 'active' : ''}`}
          onClick={() => onSelectTab('events')}
        >
          <FileText size={16} />
          <span>Security Logs</span>
        </button>
        <button
          className={`nav-tab-btn ${currentTab === 'health' ? 'active' : ''}`}
          onClick={() => onSelectTab('health')}
        >
          <Activity size={16} />
          <span>System Health</span>
        </button>
      </nav>


      {/* System Status Pill */}
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
  );
}
