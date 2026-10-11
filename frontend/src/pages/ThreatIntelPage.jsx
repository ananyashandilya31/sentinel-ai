import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldAlert,
  Search,
  Globe,
  Database,
  RefreshCw,
  AlertTriangle,
  Server,
  Activity,
  CheckCircle,
  ExternalLink,
} from 'lucide-react';
import ReputationBadge from '../components/ReputationBadge';
import RiskScoreGauge from '../components/RiskScoreGauge';
import {
  fetchThreatIntel,
  lookupIPReputation,
  seedThreatIntel,
} from '../services/api';

export default function ThreatIntelPage() {
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [reputationFilter, setReputationFilter] = useState('');
  const [minRiskFilter, setMinRiskFilter] = useState('');
  const [searchFilter, setSearchFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState(null);

  // Single IP quick lookup state
  const [lookupIpInput, setLookupIpInput] = useState('');
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState(null);

  // ─── Fetch IP Reputations ──────────────────────────────────────────────────
  const loadRecords = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchThreatIntel({
        page,
        pageSize,
        reputation: reputationFilter,
        minRisk: minRiskFilter,
        search: searchFilter,
      });
      setRecords(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err.message || 'Failed to load threat intelligence records.');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, reputationFilter, minRiskFilter, searchFilter]);

  useEffect(() => {
    loadRecords();
  }, [loadRecords]);

  // ─── Seed Database ─────────────────────────────────────────────────────────
  const handleSeed = async (overwrite = false) => {
    setSeeding(true);
    setError(null);
    try {
      await seedThreatIntel(overwrite);
      await loadRecords();
    } catch (err) {
      setError(`Seeding failed: ${err.message}`);
    } finally {
      setSeeding(false);
    }
  };

  // ─── Quick IP Lookup ───────────────────────────────────────────────────────
  const handleLookup = async (e) => {
    if (e) e.preventDefault();
    const cleanIp = lookupIpInput.trim();
    if (!cleanIp) return;

    setLookupLoading(true);
    setLookupError(null);
    setLookupResult(null);

    try {
      const result = await lookupIPReputation(cleanIp);
      setLookupResult(result);
      // Refresh table in background if newly derived
      loadRecords();
    } catch (err) {
      setLookupError(err.message || 'Unable to enrich IP.');
    } finally {
      setLookupLoading(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  // Stats summary counts
  const maliciousCount = records.filter((r) => r.reputation === 'MALICIOUS').length;
  const suspiciousCount = records.filter((r) => r.reputation === 'SUSPICIOUS').length;
  const cleanCount = records.filter((r) => r.reputation === 'CLEAN').length;

  return (
    <div className="page-container">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="page-header" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <ShieldAlert size={26} color="#f85149" />
          <div>
            <h2 className="page-title">Threat Intelligence Enrichment</h2>
            <p className="page-subtitle">
              IP Reputation · Risk Scoring · Geolocation & Autonomous System Context
            </p>
          </div>
        </div>

        <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="action-button secondary-button"
            onClick={() => handleSeed(true)}
            disabled={seeding || loading}
            title="Seed / Reset local threat database with known attack vectors"
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <RefreshCw size={14} className={seeding ? 'spin' : ''} />
            {seeding ? 'Seeding...' : 'Reset / Seed Intel'}
          </button>
        </div>
      </div>

      {/* ── Metrics Cards ───────────────────────────────────────────────────── */}
      <div className="metrics-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-title">TOTAL TRACKED IPS</span>
            <Database size={16} color="#8b949e" />
          </div>
          <div className="metric-value">{total}</div>
          <div className="metric-desc">Identified in logs & threat databases</div>
        </div>

        <div className="metric-card" style={{ borderLeft: '3px solid #f85149' }}>
          <div className="metric-header">
            <span className="metric-title">MALICIOUS IPS</span>
            <AlertTriangle size={16} color="#f85149" />
          </div>
          <div className="metric-value" style={{ color: '#f85149' }}>
            {maliciousCount}
          </div>
          <div className="metric-desc">High risk attack sources (score &ge; 70)</div>
        </div>

        <div className="metric-card" style={{ borderLeft: '3px solid #d29922' }}>
          <div className="metric-header">
            <span className="metric-title">SUSPICIOUS IPS</span>
            <Activity size={16} color="#d29922" />
          </div>
          <div className="metric-value" style={{ color: '#d29922' }}>
            {suspiciousCount}
          </div>
          <div className="metric-desc">Tor exits, scanners, or abnormal spikes</div>
        </div>

        <div className="metric-card" style={{ borderLeft: '3px solid #238636' }}>
          <div className="metric-header">
            <span className="metric-title">CLEAN / TRUSTED</span>
            <CheckCircle size={16} color="#238636" />
          </div>
          <div className="metric-value" style={{ color: '#238636' }}>
            {cleanCount}
          </div>
          <div className="metric-desc">Internal LAN & verified public services</div>
        </div>
      </div>

      {/* ── IP Quick Lookup & Enrichment Bar ─────────────────────────────────── */}
      <div
        className="card"
        style={{
          padding: '1.25rem',
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '8px',
          marginBottom: '1.5rem',
        }}
      >
        <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Search size={16} color="#58a6ff" />
          Single IP Live Lookup & Dynamic Enrichment
        </h3>
        <p style={{ fontSize: '13px', color: '#8b949e', marginBottom: '1rem' }}>
          Enter any IP address to perform live reputation lookup or dynamic heuristic risk scoring:
        </p>

        <form onSubmit={handleLookup} style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <input
            type="text"
            className="filter-input"
            style={{ flex: '1', minWidth: '220px' }}
            placeholder="e.g. 45.154.255.88, 185.220.101.5, 8.8.8.8"
            value={lookupIpInput}
            onChange={(e) => setLookupIpInput(e.target.value)}
          />
          <button
            type="submit"
            className="action-button primary-button"
            disabled={lookupLoading || !lookupIpInput.trim()}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            {lookupLoading ? <RefreshCw size={14} className="spin" /> : <Search size={14} />}
            {lookupLoading ? 'Enriching...' : 'Lookup & Enrich'}
          </button>
        </form>

        {lookupError && (
          <div style={{ marginTop: '0.75rem', color: '#f85149', fontSize: '13px' }}>
            ⚠️ {lookupError}
          </div>
        )}

        {/* Detailed Lookup Result Card */}
        {lookupResult && (
          <div
            style={{
              marginTop: '1.25rem',
              padding: '1rem',
              backgroundColor: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '18px', fontWeight: 'bold', fontFamily: 'monospace', color: '#58a6ff' }}>
                    {lookupResult.ip}
                  </span>
                  <ReputationBadge reputation={lookupResult.reputation} />
                  {lookupResult.is_tor && (
                    <span style={{ backgroundColor: '#6e40c9', color: '#fff', fontSize: '11px', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                      🧅 Tor Exit Node
                    </span>
                  )}
                  {lookupResult.is_vpn && (
                    <span style={{ backgroundColor: '#1f6feb', color: '#fff', fontSize: '11px', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                      🛡️ VPN / Proxy
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '4px' }}>
                  Source: <code>{lookupResult.source}</code> · Total Reports: {lookupResult.total_reports} · Correlated Incidents: {lookupResult.past_incidents_count}
                </div>
              </div>

              <div>
                <span style={{ fontSize: '12px', color: '#8b949e', display: 'block', marginBottom: '4px' }}>Composite Threat Risk:</span>
                <RiskScoreGauge score={lookupResult.risk_score} />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', fontSize: '13px' }}>
              <div>
                <strong style={{ color: '#8b949e' }}>Geolocation:</strong>{' '}
                <span>{lookupResult.country || 'Unknown'} {lookupResult.city ? `(${lookupResult.city})` : ''}</span>
              </div>
              <div>
                <strong style={{ color: '#8b949e' }}>ASN:</strong>{' '}
                <span>{lookupResult.asn || 'N/A'}</span>
              </div>
              <div>
                <strong style={{ color: '#8b949e' }}>ISP / Org:</strong>{' '}
                <span>{lookupResult.isp || 'N/A'}</span>
              </div>
              <div>
                <strong style={{ color: '#8b949e' }}>Threat Tags:</strong>{' '}
                {lookupResult.threat_types && lookupResult.threat_types.length > 0 ? (
                  lookupResult.threat_types.map((tag) => (
                    <span
                      key={tag}
                      style={{
                        display: 'inline-block',
                        fontSize: '11px',
                        backgroundColor: 'rgba(255, 255, 255, 0.08)',
                        padding: '1px 6px',
                        borderRadius: '3px',
                        marginRight: '4px',
                        fontFamily: 'monospace',
                      }}
                    >
                      {tag}
                    </span>
                  ))
                ) : (
                  <span style={{ color: '#8b949e' }}>None detected</span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Filter Controls ─────────────────────────────────────────────────── */}
      <div
        className="filters-bar"
        style={{
          display: 'flex',
          gap: '1rem',
          alignItems: 'center',
          flexWrap: 'wrap',
          marginBottom: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{ fontSize: '13px', color: '#8b949e' }}>Reputation:</label>
          <select
            className="filter-select"
            value={reputationFilter}
            onChange={(e) => {
              setReputationFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All Reputations</option>
            <option value="MALICIOUS">Malicious</option>
            <option value="SUSPICIOUS">Suspicious</option>
            <option value="CLEAN">Clean</option>
            <option value="UNKNOWN">Unknown</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{ fontSize: '13px', color: '#8b949e' }}>Min Risk:</label>
          <select
            className="filter-select"
            value={minRiskFilter}
            onChange={(e) => {
              setMinRiskFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Any Risk</option>
            <option value="25">&ge; 25 (Moderate)</option>
            <option value="50">&ge; 50 (High)</option>
            <option value="75">&ge; 75 (Critical)</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: '200px' }}>
          <input
            type="text"
            className="filter-input"
            style={{ width: '100%' }}
            placeholder="Search IP, country, ISP, or threat tag..."
            value={searchFilter}
            onChange={(e) => {
              setSearchFilter(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      {/* ── Error Banner ────────────────────────────────────────────────────── */}
      {error && (
        <div className="error-banner" style={{ marginBottom: '1rem' }}>
          ⚠️ {error}
        </div>
      )}

      {/* ── IP Reputation Table ─────────────────────────────────────────────── */}
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>IP ADDRESS</th>
              <th>REPUTATION</th>
              <th>RISK SCORE</th>
              <th>GEOLOCATION</th>
              <th>ASN / ISP</th>
              <th>THREAT TAGS</th>
              <th>INCIDENTS</th>
              <th>SOURCE</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: '#8b949e' }}>
                  <RefreshCw size={20} className="spin" style={{ marginBottom: '0.5rem' }} />
                  <div>Loading threat intelligence...</div>
                </td>
              </tr>
            ) : records.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: '#8b949e' }}>
                  No threat intelligence records matched your query.
                </td>
              </tr>
            ) : (
              records.map((item) => (
                <tr key={item.ip}>
                  <td>
                    <button
                      type="button"
                      onClick={() => {
                        setLookupIpInput(item.ip);
                        lookupIPReputation(item.ip).then(setLookupResult).catch(() => {});
                      }}
                      style={{
                        background: 'none',
                        border: 'none',
                        padding: 0,
                        fontFamily: 'monospace',
                        fontWeight: 'bold',
                        color: '#58a6ff',
                        cursor: 'pointer',
                        textAlign: 'left',
                      }}
                      title="Click to inspect full details in enrichment card"
                    >
                      {item.ip}
                    </button>
                    <div style={{ display: 'flex', gap: '4px', marginTop: '2px' }}>
                      {item.is_tor && (
                        <span style={{ fontSize: '10px', backgroundColor: '#6e40c9', color: '#fff', padding: '1px 4px', borderRadius: '3px' }}>
                          Tor
                        </span>
                      )}
                      {item.is_vpn && (
                        <span style={{ fontSize: '10px', backgroundColor: '#1f6feb', color: '#fff', padding: '1px 4px', borderRadius: '3px' }}>
                          VPN
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <ReputationBadge reputation={item.reputation} />
                  </td>
                  <td>
                    <RiskScoreGauge score={item.risk_score} />
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Globe size={13} color="#8b949e" />
                      <span>{item.country || 'Unknown'}</span>
                    </div>
                    {item.city && (
                      <div style={{ fontSize: '11px', color: '#8b949e' }}>{item.city}</div>
                    )}
                  </td>
                  <td>
                    <div style={{ fontSize: '12px' }}>{item.isp || 'N/A'}</div>
                    {item.asn && (
                      <div style={{ fontSize: '11px', color: '#8b949e', fontFamily: 'monospace' }}>
                        {item.asn}
                      </div>
                    )}
                  </td>
                  <td>
                    {item.threat_types && item.threat_types.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                        {item.threat_types.map((tag) => (
                          <span
                            key={tag}
                            style={{
                              fontSize: '11px',
                              backgroundColor: 'rgba(255, 255, 255, 0.08)',
                              padding: '1px 6px',
                              borderRadius: '3px',
                              fontFamily: 'monospace',
                            }}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span style={{ color: '#8b949e', fontSize: '12px' }}>—</span>
                    )}
                  </td>
                  <td>
                    <span
                      style={{
                        fontWeight: item.past_incidents_count > 0 ? 'bold' : 'normal',
                        color: item.past_incidents_count > 0 ? '#f85149' : '#8b949e',
                      }}
                    >
                      {item.past_incidents_count}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '11px', color: '#8b949e' }}>
                      {item.source}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* ── Pagination ──────────────────────────────────────────────────────── */}
      <div
        className="pagination-controls"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '1rem',
          fontSize: '13px',
          color: '#8b949e',
        }}
      >
        <div>
          Showing page {page} of {totalPages} ({total} total IP records)
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className="action-button secondary-button"
            disabled={page <= 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </button>
          <button
            className="action-button secondary-button"
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
