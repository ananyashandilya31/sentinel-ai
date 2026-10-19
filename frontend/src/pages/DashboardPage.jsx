import React, { useEffect, useState, useCallback } from 'react';
import {
  Activity,
  Flame,
  AlertTriangle,
  ShieldAlert,
  FileSearch,
  Radio,
  Wifi,
  WifiOff,
  RefreshCw,
  ArrowRight,
} from 'lucide-react';
import { fetchIncidents, fetchLogs } from '../services/api';
import { useLiveAlerts } from '../hooks/useLiveAlerts';
import SeverityBadge from '../components/SeverityBadge';
import StatusBadge from '../components/StatusBadge';
import { WS_STATE } from '../services/ws';

/**
 * DashboardPage — the real-time SOC console (Phase 7).
 *
 * Pulls baseline counters over REST, then keeps them fresh via the
 * /ws/alerts WebSocket stream: new incidents appear instantly,
 * counters tick up, and the live feed shows every streamed event.
 */
export default function DashboardPage({ onOpenIncidents }) {
  // REST-fetched baseline
  const [incidents, setIncidents] = useState([]);
  const [totalIncidents, setTotalIncidents] = useState(0);
  const [totalEvents, setTotalEvents] = useState(0);
  const [recentLogs, setRecentLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Live stream
  const { events, connectionState, incidentEvents } = useLiveAlerts();

  const loadBaseline = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      // Fetch all incidents to compute severity counters and recent logs for feed
      const [incRes, logRes] = await Promise.all([
        fetchIncidents({ page: 1, pageSize: 100 }),
        fetchLogs({ page: 1, pageSize: 12 }),
      ]);
      const items = incRes.items || [];
      setIncidents(items);
      setTotalIncidents(incRes.total || 0);
      setTotalEvents(logRes.total || 0);
      setRecentLogs(logRes.items || []);
    } catch (err) {
      console.error('Dashboard load failed:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadBaseline();
    // Re-pull the baseline periodically as a safety net (every 60s)
    const interval = setInterval(() => loadBaseline(true), 60000);
    return () => clearInterval(interval);
  }, [loadBaseline]);

  // ── Derived counters ───────────────────────────────────────────
  const openIncidents = incidents.filter(
    (i) => i.status === 'OPEN' || i.status === 'INVESTIGATING'
  );
  const criticalCount = incidents.filter((i) => i.severity === 'CRITICAL').length;
  const highCount = incidents.filter((i) => i.severity === 'HIGH').length;
  const mediumCount = incidents.filter((i) => i.severity === 'MEDIUM').length;

  // Merge live NEW_INCIDENT events into the displayed list (dedup by id)
  const liveIncidentMap = new Map();
  incidentEvents
    .filter((e) => e.type === 'NEW_INCIDENT' && e.incident)
    .forEach((e) => liveIncidentMap.set(e.incident.id, e.incident));
  const displayIncidents = [
    ...Array.from(liveIncidentMap.values()).filter(
      (li) => !incidents.some((i) => i.id === li.id)
    ),
    ...incidents,
  ].slice(0, 8);

  // ── Live activity feed (pre-seeded with recent security logs) ──
  const logFeedItems = (recentLogs || []).map((l) => ({
    id: l.id,
    type: l.event_type || 'SECURITY_LOG',
    timestamp: l.timestamp,
    message: `${l.user || 'system'} · ${l.ip || ''} · ${l.port ? `port ${l.port}` : 'internal'} · ${l.status || 'PROCESSED'}`,
  }));

  // Show live events first; backfill with recent security logs
  const combinedEvents = [...events, ...logFeedItems];
  const feed = combinedEvents.slice(0, 12);

  const isLive = connectionState === WS_STATE.OPEN;
  const isUnauthorized = connectionState === WS_STATE.UNAUTHORIZED;

  const formatTimestamp = (isoStr) => {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleTimeString('en-US', { hour12: false });
  };

  const formatDateTime = (isoStr) => {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const connectionLabel = {
    [WS_STATE.OPEN]: 'LIVE',
    [WS_STATE.CONNECTING]: 'CONNECTING',
    [WS_STATE.RECONNECTING]: 'RECONNECTING',
    [WS_STATE.UNAUTHORIZED]: 'UNAUTHORIZED',
    [WS_STATE.CLOSED]: 'OFFLINE',
  }[connectionState] || 'OFFLINE';

  return (
    <div>
      {/* Header with live indicator */}
      <div className="phase-banner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div>
            <div className="phase-title">Security Operations Dashboard</div>
            <div className="phase-description">
              Real-time threat monitoring, live WebSocket alert stream, and event telemetry.
            </div>
          </div>
          <div
            className={`system-status-pill ${isLive ? 'badge-connected' : 'badge-disconnected'}`}
            style={{ marginLeft: '1rem' }}
          >
            <span
              className={`status-indicator ${isLive ? 'pulse' : ''}`}
              style={{
                backgroundColor: isLive
                  ? 'var(--accent-green)'
                  : 'var(--accent-amber)',
              }}
            />
            <Radio size={12} />
            {connectionLabel}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button className="action-btn" onClick={() => loadBaseline(true)} disabled={refreshing}>
            <RefreshCw size={14} className={refreshing ? 'pulse' : ''} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Connection offline warning */}
      {!isLive && (
        <div
          style={{
            padding: '0.6rem 1rem',
            marginBottom: '1.25rem',
            borderRadius: '6px',
            fontSize: '0.8rem',
            background: isUnauthorized
              ? 'rgba(239, 68, 68, 0.12)'
              : 'rgba(245, 158, 11, 0.1)',
            border: isUnauthorized
              ? 'var(--accent-red)'
              : 'var(--accent-amber)',
            color: isUnauthorized ? 'var(--accent-red)' : 'var(--accent-amber)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <WifiOff size={14} />
          {isUnauthorized
            ? 'Live stream rejected the session token — sign in again to resume live alerts.'
            : `Live stream unavailable (${connectionLabel}) — showing last known state. Retrying automatically…`}
        </div>
      )}

      {/* Counters */}
      <div className="grid-cards" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-red)' }}>
          <div className="card-header">
            <span className="card-title"><Flame size={15} color="var(--accent-red)" /> Critical</span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-red)' }}>{criticalCount}</div>
          <div className="metric-sub">Immediate action required</div>
        </div>

        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-amber)' }}>
          <div className="card-header">
            <span className="card-title"><AlertTriangle size={15} color="var(--accent-amber)" /> High</span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-amber)' }}>{highCount}</div>
          <div className="metric-sub">Brute force & privilege elevation</div>
        </div>

        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-purple)' }}>
          <div className="card-header">
            <span className="card-title"><ShieldAlert size={15} color="var(--accent-purple)" /> Medium</span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-purple)' }}>{mediumCount}</div>
          <div className="metric-sub">Port scanning & reconnaissance</div>
        </div>

        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-cyan)' }}>
          <div className="card-header">
            <span className="card-title"><FileSearch size={15} color="var(--accent-cyan)" /> Open Incidents</span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-cyan)' }}>{openIncidents.length}</div>
          <div className="metric-sub">of {totalIncidents} total incidents</div>
        </div>

        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-green)' }}>
          <div className="card-header">
            <span className="card-title"><Activity size={15} color="var(--accent-green)" /> Total Events</span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-green)' }}>
            {totalEvents.toLocaleString()}
          </div>
          <div className="metric-sub">Ingested security logs</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '1.25rem', alignItems: 'start' }}>
        {/* Active incidents */}
        <div className="table-container">
          <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Wifi size={15} color={isLive ? 'var(--accent-green)' : 'var(--text-muted)'} />
            Active Incidents
            {isLive && <span className="live-dot" />}
          </div>
          <table className="soc-table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Attack Type</th>
                <th>Title</th>
                <th>Status</th>
                <th>Detected At</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '2.5rem' }}>
                    <span style={{ color: 'var(--accent-cyan)' }}>Loading dashboard...</span>
                  </td>
                </tr>
              ) : displayIncidents.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '2.5rem' }}>
                    <ShieldAlert size={30} color="var(--text-muted)" style={{ marginBottom: '0.5rem' }} />
                    <div style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>No active incidents</div>
                    <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                      Run a detection scan or seed attack logs — alerts stream in live.
                    </div>
                  </td>
                </tr>
              ) : (
                displayIncidents.map((inc) => (
                  <tr key={inc.id} style={{ cursor: 'pointer' }} onClick={() => onOpenIncidents && onOpenIncidents()}>
                    <td><SeverityBadge severity={inc.severity} /></td>
                    <td><span className="type-badge">{String(inc.type || '').replace('_', ' ')}</span></td>
                    <td style={{ fontWeight: 600 }}>{inc.title}</td>
                    <td><StatusBadge status={inc.status} /></td>
                    <td className="mono-cell">{formatDateTime(inc.created_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Live alert feed */}
        <div className="table-container">
          <div className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={15} color="var(--accent-cyan)" />
            Live Event Stream
            {isLive && <span className="live-dot" />}
          </div>
          <div className="live-feed" style={{ maxHeight: '420px', overflowY: 'auto' }}>
            {feed.length === 0 ? (
              <div style={{ padding: '2rem 1rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                {isLive
                  ? 'Connected — waiting for detection events…'
                  : 'Stream offline'}
              </div>
            ) : (
              feed.map((evt, idx) => (
                <div key={evt.id || `${evt.type}-${idx}`} className="feed-item">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="feed-type">{String(evt.type || 'EVENT').replace(/_/g, ' ')}</span>
                    <span className="feed-time">{formatTimestamp(evt.timestamp)}</span>
                  </div>
                  <div className="feed-body">
                    {evt.incident
                      ? `${evt.incident.severity || ''} · ${evt.incident.title || ''}`
                      : evt.message || evt.status || ''}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Activity sparkline: events per feed bucket (last 12 events) */}
      <div className="table-container" style={{ marginTop: '1.25rem' }}>
        <div className="section-title">
          <Activity size={15} color="var(--accent-green)" />
          Stream Activity (last {feed.length} events)
        </div>
        <div className="activity-chart">
          {feed.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', padding: '1rem 0' }}>
              No activity yet
            </div>
          ) : (
            [...feed].reverse().map((evt, idx) => {
              const weight = evt.type === 'NEW_INCIDENT' ? 1 : 0.45;
              const color =
                evt.incident?.severity === 'CRITICAL'
                  ? 'var(--accent-red)'
                  : evt.incident?.severity === 'HIGH'
                  ? 'var(--accent-amber)'
                  : evt.type === 'NEW_INCIDENT'
                  ? 'var(--accent-cyan)'
                  : 'var(--accent-green)';
              const heightPct = Math.round(weight * 60 + ((idx * 11) % 25) + 15);
              return (
                <div
                  key={evt.id || `bar-${idx}`}
                  className="activity-bar"
                  title={`${evt.type}${evt.incident ? ` — ${evt.incident.title}` : ''}`}
                  style={{
                    flex: weight,
                    height: `${heightPct}%`,
                    backgroundColor: color,
                    opacity: 0.35 + (0.65 * (idx + 1)) / Math.max(feed.length, 1),
                  }}
                />
              );
            })
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
          <span>oldest</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <ArrowRight size={11} /> latest
          </span>
        </div>
      </div>
    </div>
  );
}
