import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import HealthPage from './pages/HealthPage';
import EventsPage from './pages/EventsPage';
import IncidentsPage from './pages/IncidentsPage';
import { fetchHealthStatus } from './services/api';

export default function App() {
  const [currentTab, setCurrentTab] = useState('incidents'); // Default to Incidents in Phase 3
  const [openIncidentsCount, setOpenIncidentsCount] = useState(0);
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

  return (
    <div className="soc-app">
      {/* Top Navbar */}
      <Navbar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        systemStatus={{ isApiOnline, isDbConnected }}
        openIncidentsCount={openIncidentsCount}
      />

      {/* Main SOC Content */}
      <main className="soc-content">
        {currentTab === 'incidents' && (
          <IncidentsPage onIncidentCountChange={setOpenIncidentsCount} />
        )}
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
        SentinelAI SOC — AI-Powered Security Operations Center • Phase 3 Detection Engine Active
      </footer>
    </div>
  );
}
