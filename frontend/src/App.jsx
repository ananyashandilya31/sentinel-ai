import React, { useState, useEffect, useCallback, useRef } from 'react';
import Navbar from './components/Navbar';
import DashboardPage from './pages/DashboardPage';
import HealthPage from './pages/HealthPage';
import EventsPage from './pages/EventsPage';
import IncidentsPage from './pages/IncidentsPage';
import MLPredictionsPage from './pages/MLPredictionsPage';
import ThreatIntelPage from './pages/ThreatIntelPage';
import LoginPage from './pages/LoginPage';
import NotificationToast from './components/NotificationToast';
import { useLiveAlerts } from './hooks/useLiveAlerts';
import { useAuth } from './context/AuthContext';
import { fetchHealthStatus } from './services/api';

export default function App() {
  const { isAuthenticated, loading: authLoading } = useAuth();
  const [currentTab, setCurrentTab] = useState('dashboard'); // Phase 7: live dashboard first
  const [openIncidentsCount, setOpenIncidentsCount] = useState(0);
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [latency, setLatency] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastChecked, setLastChecked] = useState(null);

  // Global live alert stream — powers toasts everywhere
  const { incidentEvents } = useLiveAlerts();
  const [toasts, setToasts] = useState([]);
  const seenIncidentIds = useRef(new Set());

  // Turn every NEW_INCIDENT live event into a toast notification
  useEffect(() => {
    incidentEvents.forEach((evt) => {
      if (evt.type !== 'NEW_INCIDENT' || !evt.incident) return;
      const id = evt.incident.id;
      if (seenIncidentIds.current.has(id)) return;
      seenIncidentIds.current.add(id);
      setToasts((prev) => [
        ...prev.slice(-4), // keep at most 5 stacked toasts
        { id: `${id}-${evt.timestamp || Date.now()}`, incident: evt.incident },
      ]);
    });
  }, [incidentEvents]);

  const dismissToast = useCallback((toastId) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId));
  }, []);

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

  // ── Auth gate ───────────────────────────────────────────────────
  if (authLoading) {
    return (
      <div className="soc-app">
        <div className="page-container" style={{ textAlign: 'center', paddingTop: '4rem' }}>
          <span style={{ color: 'var(--accent-cyan)' }}>Validating session…</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="soc-app">
        <LoginPage />
      </div>
    );
  }

  const isApiOnline = !!healthData;
  const isDbConnected = healthData?.database?.status === 'connected';
  const systemHealthStatus = healthData?.status || (isApiOnline ? 'degraded' : 'error');

  return (
    <div className="soc-app">
      {/* Top Navbar */}
      <Navbar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        systemStatus={{ isApiOnline, isDbConnected, status: systemHealthStatus, loading }}
        openIncidentsCount={openIncidentsCount}
      />

      {/* Live alert toasts */}
      <NotificationToast toasts={toasts} onDismiss={dismissToast} />

      {/* Main SOC Content */}
      <main className="soc-content">
        {currentTab === 'dashboard' && (
          <DashboardPage onOpenIncidents={() => setCurrentTab('incidents')} />
        )}
        {currentTab === 'incidents' && (
          <IncidentsPage onIncidentCountChange={setOpenIncidentsCount} />
        )}
        {currentTab === 'ml' && <MLPredictionsPage />}
        {currentTab === 'threat-intel' && <ThreatIntelPage />}
        {currentTab === 'events' && <EventsPage />}
        {currentTab === 'health' && (
          <HealthPage
            healthData={healthData}
            loading={loading}
            latency={latency}
            errorMsg={errorMsg}
            lastChecked={lastChecked}
            autoRefresh={autoRefresh}
            setAutoRefresh={setAutoRefresh}
            onCheckHealth={checkHealth}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="soc-footer">
        SentinelAI SOC — AI-Powered Security Operations Center • System Operational
      </footer>
    </div>
  );
}
