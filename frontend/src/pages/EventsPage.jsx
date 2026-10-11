import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Filter,
  RefreshCw,
  Database,
  ArrowLeft,
  ArrowRight,
  ShieldAlert,
  Download,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { fetchLogs, seedLogs } from '../services/api';
import EventTypeBadge from '../components/EventTypeBadge';

export default function EventsPage() {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // Filters
  const [search, setSearch] = useState('');
  const [eventType, setEventType] = useState('');
  const [userFilter, setUserFilter] = useState('');
  const [ipFilter, setIpFilter] = useState('');

  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const loadLogs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchLogs({
        page,
        pageSize,
        user: userFilter,
        ip: ipFilter,
        eventType,
        search,
      });
      setLogs(data.items || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
    } catch (err) {
      console.error(err);
      setActionMessage({
        type: 'error',
        text: 'Failed to retrieve logs. Check if backend is reachable.',
      });
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, userFilter, ipFilter, eventType, search]);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const handleSeed = async () => {
    setSeeding(true);
    setActionMessage(null);
    try {
      const result = await seedLogs(250);
      setActionMessage({
        type: 'success',
        text: result.message || 'Demo logs seeded successfully!',
      });
      setPage(1);
      await loadLogs();
    } catch (err) {
      setActionMessage({
        type: 'error',
        text: err.message || 'Failed to seed logs.',
      });
    } finally {
      setSeeding(false);
    }
  };

  const handleResetFilters = () => {
    setSearch('');
    setEventType('');
    setUserFilter('');
    setIpFilter('');
    setPage(1);
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

  return (
    <div>
      {/* Top Header & Action Controls */}
      <div className="phase-banner">
        <div>
          <div className="phase-title">Phase 2: Security Events Explorer</div>
          <div className="phase-description">
            Ingested security logs with multi-field search, event type filtering, and real-time pagination.
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="action-btn"
            onClick={handleSeed}
            disabled={seeding || loading}
            title="Populate database with synthetic dataset containing benign traffic and injected attacks"
          >
            <Download size={14} className={seeding ? 'pulse' : ''} />
            {seeding ? 'Seeding...' : 'Seed Demo Logs'}
          </button>
          <button
            className="action-btn"
            onClick={loadLogs}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'pulse' : ''} />
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Action Notification Toast */}
      {actionMessage && (
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
              actionMessage.type === 'success'
                ? 'rgba(16, 185, 129, 0.15)'
                : 'rgba(239, 68, 68, 0.15)',
            border:
              actionMessage.type === 'success'
                ? '1px solid var(--accent-green)'
                : '1px solid var(--accent-red)',
            color:
              actionMessage.type === 'success'
                ? 'var(--accent-green)'
                : 'var(--accent-red)',
          }}
        >
          {actionMessage.type === 'success' ? (
            <CheckCircle size={16} />
          ) : (
            <AlertCircle size={16} />
          )}
          <span>{actionMessage.text}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="filter-bar">
        <div className="search-box">
          <Search size={16} color="var(--text-muted)" />
          <input
            type="text"
            placeholder="Search across user, IP, or session..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>

        <select
          className="filter-select"
          value={eventType}
          onChange={(e) => {
            setEventType(e.target.value);
            setPage(1);
          }}
        >
          <option value="">All Event Types</option>
          <option value="LOGIN_FAILED">LOGIN_FAILED</option>
          <option value="LOGIN_SUCCESS">LOGIN_SUCCESS</option>
          <option value="DATA_TRANSFER">DATA_TRANSFER</option>
          <option value="PORT_CONNECT">PORT_CONNECT</option>
          <option value="PRIVILEGE_CHANGE">PRIVILEGE_CHANGE</option>
        </select>

        <input
          type="text"
          className="filter-input"
          placeholder="Filter by user..."
          value={userFilter}
          onChange={(e) => {
            setUserFilter(e.target.value);
            setPage(1);
          }}
        />

        <input
          type="text"
          className="filter-input"
          placeholder="Filter by IP..."
          value={ipFilter}
          onChange={(e) => {
            setIpFilter(e.target.value);
            setPage(1);
          }}
        />

        {(search || eventType || userFilter || ipFilter) && (
          <button className="reset-btn" onClick={handleResetFilters}>
            Clear
          </button>
        )}
      </div>

      {/* Security Logs Data Table */}
      <div className="table-container">
        <table className="soc-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>User</th>
              <th>Source IP</th>
              <th>Event Type</th>
              <th>Port</th>
              <th>Data Volume</th>
              <th>Country</th>
              <th>Session ID</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '3rem' }}>
                  <span style={{ color: 'var(--accent-cyan)' }}>Loading security logs...</span>
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan="8" style={{ textAlign: 'center', padding: '3.5rem' }}>
                  <ShieldAlert size={36} color="var(--text-muted)" style={{ marginBottom: '0.75rem' }} />
                  <div style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>No security events found</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                    Click <strong>"Seed Demo Logs"</strong> above to populate the database with realistic security traffic and attacks.
                  </div>
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td className="mono-cell">{formatTimestamp(log.timestamp)}</td>
                  <td>
                    <span className="user-badge">{log.user}</span>
                  </td>
                  <td className="mono-cell">{log.ip}</td>
                  <td>
                    <EventTypeBadge eventType={log.event_type} />
                  </td>
                  <td className="mono-cell">{log.port ?? '—'}</td>
                  <td className="mono-cell">{formatBytes(log.bytes_transferred)}</td>
                  <td>
                    <span className="country-tag">{log.country}</span>
                  </td>
                  <td className="mono-cell" style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                    {log.session_id}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="pagination-bar">
        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Showing <strong>{logs.length}</strong> of <strong>{total}</strong> events (Page {page} of {totalPages})
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <select
            className="page-size-select"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setPage(1);
            }}
          >
            <option value="10">10 / page</option>
            <option value="20">20 / page</option>
            <option value="50">50 / page</option>
          </select>

          <button
            className="page-btn"
            disabled={page <= 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ArrowLeft size={14} /> Previous
          </button>

          <button
            className="page-btn"
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
