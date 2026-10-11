import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  Play,
  RefreshCw,
  Eye,
  X,
  UserCheck,
  CheckCircle,
  FileSearch,
  ExternalLink,
  Flame,
} from 'lucide-react';
import {
  fetchIncidents,
  fetchIncidentById,
  updateIncidentStatus,
  evaluateDetection,
} from '../services/api';
import SeverityBadge from '../components/SeverityBadge';
import StatusBadge from '../components/StatusBadge';
import EventTypeBadge from '../components/EventTypeBadge';

export default function IncidentsPage({ onIncidentCountChange }) {
  const [incidents, setIncidents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Filters
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');

  const [loading, setLoading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [toastMsg, setToastMsg] = useState(null);

  // Selected incident for slide-out inspection drawer
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [assigneeInput, setAssigneeInput] = useState('');

  const loadIncidents = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchIncidents({
        page,
        pageSize,
        severity: severityFilter,
        status: statusFilter,
        type: typeFilter,
      });
      setIncidents(data.items || []);
      setTotal(data.total || 0);

      // Report active/open incident count to Navbar
      const openCount = (data.items || []).filter(
        (i) => i.status === 'OPEN' || i.status === 'INVESTIGATING'
      ).length;
      if (onIncidentCountChange) onIncidentCountChange(openCount);
    } catch (err) {
      console.error(err);
      setToastMsg({ type: 'error', text: 'Failed to retrieve incidents.' });
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, severityFilter, statusFilter, typeFilter, onIncidentCountChange]);

  useEffect(() => {
    loadIncidents();
  }, [loadIncidents]);

  const handleOpenDetail = async (incidentId) => {
    setDetailLoading(true);
    try {
      const detail = await fetchIncidentById(incidentId);
      setSelectedIncident(detail);
      setAssigneeInput(detail.assigned_to || '');
    } catch (err) {
      console.error(err);
      setToastMsg({ type: 'error', text: 'Failed to load incident details.' });
    } finally {
      setDetailLoading(false);
    }
  };

  const handleUpdateStatus = async (newStatus) => {
    if (!selectedIncident) return;
    setUpdatingStatus(true);
    try {
      const updated = await updateIncidentStatus(selectedIncident.id, {
        status: newStatus,
        assigned_to: assigneeInput || null,
      });
      setSelectedIncident(updated);
      setToastMsg({ type: 'success', text: `Incident updated to ${newStatus}` });
      await loadIncidents();
    } catch (err) {
      setToastMsg({ type: 'error', text: 'Failed to update incident.' });
    } finally {
      setUpdatingStatus(false);
    }
  };

  const handleRunDetection = async () => {
    setEvaluating(true);
    setToastMsg(null);
    try {
      const res = await evaluateDetection();
      setToastMsg({
        type: 'success',
        text: res.message || 'Detection scan completed successfully!',
      });
      await loadIncidents();
    } catch (err) {
      setToastMsg({ type: 'error', text: err.message || 'Detection execution failed.' });
    } finally {
      setEvaluating(false);
    }
  };

  const formatTimestamp = (isoStr) => {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const formatBytes = (bytes) => {
    if (!bytes && bytes !== 0) return '—';
    if (bytes >= 1_048_576) {
      return `${(bytes / 1_048_576).toFixed(1)} MB`;
    }
    if (bytes >= 1_024) {
      return `${(bytes / 1_024).toFixed(1)} KB`;
    }
    return `${bytes} B`;
  };

  // Metrics summary
  const criticalCount = incidents.filter((i) => i.severity === 'CRITICAL').length;
  const highCount = incidents.filter((i) => i.severity === 'HIGH').length;
  const mediumCount = incidents.filter((i) => i.severity === 'MEDIUM').length;

  return (
    <div>
      {/* Banner & Actions */}
      <div className="phase-banner">
        <div>
          <div className="phase-title">Phase 3: Active Incidents & Correlation</div>
          <div className="phase-description">
            Detection rules (Brute Force, Port Scan, Exfiltration, Account Compromise, Privilege Escalation) with correlated evidence.
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="action-btn"
            onClick={handleRunDetection}
            disabled={evaluating || loading}
            title="Scan security logs through all detection rules"
          >
            <Play size={14} className={evaluating ? 'pulse' : ''} />
            {evaluating ? 'Scanning...' : 'Run Detection Scan'}
          </button>
          <button className="action-btn" onClick={loadIncidents} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'pulse' : ''} />
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Toast Feedback */}
      {toastMsg && (
        <div
          style={{
            padding: '0.75rem 1rem',
            borderRadius: '6px',
            marginBottom: '1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.85rem',
            background:
              toastMsg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            border:
              toastMsg.type === 'success'
                ? '1px solid var(--accent-green)'
                : '1px solid var(--accent-red)',
            color: toastMsg.type === 'success' ? 'var(--accent-green)' : 'var(--accent-red)',
          }}
        >
          {toastMsg.type === 'success' ? <CheckCircle size={16} /> : <AlertTriangle size={16} />}
          <span>{toastMsg.text}</span>
        </div>
      )}

      {/* Triage Metrics Grid */}
      <div className="grid-cards" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-red)' }}>
          <div className="card-header">
            <span className="card-title">
              <Flame size={15} color="var(--accent-red)" /> Critical Attacks
            </span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-red)' }}>
            {criticalCount}
          </div>
          <div className="metric-sub">Immediate action required</div>
        </div>

        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-amber)' }}>
          <div className="card-header">
            <span className="card-title">
              <AlertTriangle size={15} color="var(--accent-amber)" /> High Severity
            </span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-amber)' }}>
            {highCount}
          </div>
          <div className="metric-sub">Brute force & privilege elevation</div>
        </div>

        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-purple)' }}>
          <div className="card-header">
            <span className="card-title">
              <ShieldAlert size={15} color="var(--accent-purple)" /> Medium
            </span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-purple)' }}>
            {mediumCount}
          </div>
          <div className="metric-sub">Port scanning & reconnaissance</div>
        </div>

        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-cyan)' }}>
          <div className="card-header">
            <span className="card-title">
              <FileSearch size={15} color="var(--accent-cyan)" /> Total Incidents
            </span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-cyan)' }}>
            {total}
          </div>
          <div className="metric-sub">Correlated across log stream</div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <select
          className="filter-select"
          value={severityFilter}
          onChange={(e) => {
            setSeverityFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All Severities</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="HIGH">HIGH</option>
          <option value="MEDIUM">MEDIUM</option>
          <option value="LOW">LOW</option>
        </select>

        <select
          className="filter-select"
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All Statuses</option>
          <option value="OPEN">OPEN</option>
          <option value="INVESTIGATING">INVESTIGATING</option>
          <option value="RESOLVED">RESOLVED</option>
          <option value="FALSE_POSITIVE">FALSE POSITIVE</option>
        </select>

        <select
          className="filter-select"
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All Attack Types</option>
          <option value="BRUTE_FORCE">BRUTE FORCE</option>
          <option value="PORT_SCAN">PORT SCAN</option>
          <option value="DATA_EXFILTRATION">DATA EXFILTRATION</option>
          <option value="ACCOUNT_COMPROMISE">ACCOUNT COMPROMISE</option>
          <option value="PRIVILEGE_ESCALATION">PRIVILEGE ESCALATION</option>
        </select>

        {(severityFilter || statusFilter || typeFilter) && (
          <button
            className="reset-btn"
            onClick={() => {
              setSeverityFilter('');
              setStatusFilter('');
              setTypeFilter('');
              setPage(1);
            }}
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Incidents Table */}
      <div className="table-container">
        <table className="soc-table">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Attack Type</th>
              <th>Incident Title</th>
              <th>Status</th>
              <th>Evidence</th>
              <th>Assignee</th>
              <th>Detected At</th>
              <th style={{ textAlign: 'center' }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '3rem' }}>
                  <span style={{ color: 'var(--accent-cyan)' }}>Loading security incidents...</span>
                </td>
              </tr>
            ) : incidents.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '3.5rem' }}>
                  <ShieldAlert size={36} color="var(--text-muted)" style={{ marginBottom: '0.75rem' }} />
                  <div style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>No incidents found</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                    Click <strong>"Run Detection Scan"</strong> or seed attack logs on the Security Logs page to trigger alerts.
                  </div>
                </td>
              </tr>
            ) : (
              incidents.map((inc) => (
                <tr key={inc.id} style={{ cursor: 'pointer' }} onClick={() => handleOpenDetail(inc.id)}>
                  <td>
                    <SeverityBadge severity={inc.severity} />
                  </td>
                  <td>
                    <span className="type-badge">{inc.type.replace('_', ' ')}</span>
                  </td>
                  <td style={{ fontWeight: 600 }}>{inc.title}</td>
                  <td>
                    <StatusBadge status={inc.status} />
                  </td>
                  <td>
                    <span className="evidence-pill">{inc.evidence_count} logs</span>
                  </td>
                  <td>
                    <span style={{ color: inc.assigned_to ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                      {inc.assigned_to || 'Unassigned'}
                    </span>
                  </td>
                  <td className="mono-cell">{formatTimestamp(inc.created_at)}</td>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      className="view-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenDetail(inc.id);
                      }}
                    >
                      <Eye size={13} /> Triage
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Investigation Detail Modal / Drawer */}
      {selectedIncident && (
        <div className="drawer-overlay" onClick={() => setSelectedIncident(null)}>
          <div className="incident-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.3rem' }}>
                  <SeverityBadge severity={selectedIncident.severity} />
                  <span className="type-badge">{selectedIncident.type}</span>
                  <StatusBadge status={selectedIncident.status} />
                </div>
                <h2 style={{ fontSize: '1.2rem', color: '#ffffff' }}>{selectedIncident.title}</h2>
              </div>
              <button className="close-btn" onClick={() => setSelectedIncident(null)}>
                <X size={18} />
              </button>
            </div>

            <div className="drawer-body">
              {/* Analyst Triage Controls */}
              <div className="triage-panel">
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
                  <div>
                    <label className="drawer-label">Update Status</label>
                    <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.25rem' }}>
                      {['OPEN', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE'].map((st) => (
                        <button
                          key={st}
                          className={`status-toggle-btn ${selectedIncident.status === st ? 'active' : ''}`}
                          onClick={() => handleUpdateStatus(st)}
                          disabled={updatingStatus}
                        >
                          {st.replace('_', ' ')}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label className="drawer-label">Assigned Analyst</label>
                    <div style={{ display: 'flex', gap: '0.4rem', marginTop: '0.25rem' }}>
                      <input
                        type="text"
                        className="filter-input"
                        style={{ width: '100%' }}
                        placeholder="e.g. analyst_sarah"
                        value={assigneeInput}
                        onChange={(e) => setAssigneeInput(e.target.value)}
                      />
                      <button
                        className="action-btn"
                        onClick={() => handleUpdateStatus(selectedIncident.status)}
                        disabled={updatingStatus}
                      >
                        <UserCheck size={14} /> Assign
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Triggered Alerts Section */}
              <div style={{ marginBottom: '1.5rem' }}>
                <h3 className="section-title">Triggered Detection Alerts</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {selectedIncident.alerts.map((al) => (
                    <div key={al.id} className="alert-item">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{al.rule_name}</span>
                        <SeverityBadge severity={al.severity} />
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                        Triggered: {formatTimestamp(al.created_at)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Correlated Evidence Logs Section */}
              <div>
                <h3 className="section-title">
                  Correlated Evidence Logs ({selectedIncident.evidence.length})
                </h3>
                <div className="table-container" style={{ maxHeight: '350px', overflowY: 'auto' }}>
                  <table className="soc-table" style={{ fontSize: '0.78rem' }}>
                    <thead>
                      <tr>
                        <th>Timestamp</th>
                        <th>User</th>
                        <th>Source IP</th>
                        <th>Event</th>
                        <th>Port</th>
                        <th>Volume</th>
                        <th>Evidence Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedIncident.evidence.map((ev) => (
                        <tr key={ev.id}>
                          <td className="mono-cell">{formatTimestamp(ev.log?.timestamp || ev.created_at)}</td>
                          <td><span className="user-badge">{ev.log?.user || '—'}</span></td>
                          <td className="mono-cell">{ev.log?.ip || '—'}</td>
                          <td><EventTypeBadge eventType={ev.log?.event_type} /></td>
                          <td className="mono-cell">{ev.log?.port ?? '—'}</td>
                          <td className="mono-cell">{formatBytes(ev.log?.bytes_transferred)}</td>
                          <td style={{ color: 'var(--accent-cyan)' }}>{ev.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
