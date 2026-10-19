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
  ArrowLeft,
  ArrowRight,
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
    <div>
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="phase-banner">
        <div>
          <div className="phase-title">Threat Intelligence</div>
          <div className="phase-description">
            IP reputation, risk scoring, geolocation, and autonomous system context.
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <button
            className="action-btn"
            onClick={() => handleSeed(true)}
            disabled={seeding || loading}
            title="Seed / Reset local threat database with known attack vectors"
          >
            <RefreshCw size={14} className={seeding ? 'pulse' : ''} />
            {seeding ? 'Seeding...' : 'Reset / Seed Intel'}
          </button>
        </div>
      </div>

      {/* ── Metrics Cards ───────────────────────────────────────────────────── */}
      <div className="grid-cards" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-cyan)' }}>
          <div className="card-header">
            <span className="card-title">
              <Database size={15} color="var(--accent-cyan)" /> Total Tracked IPs
            </span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-cyan)' }}>{total}</div>
          <div className="metric-sub">Identified in logs &amp; threat databases</div>
        </div>

        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-red)' }}>
          <div className="card-header">
            <span className="card-title">
              <AlertTriangle size={15} color="var(--accent-red)" /> Malicious IPs
            </span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-red)' }}>
            {maliciousCount}
          </div>
          <div className="metric-sub">High risk attack sources (score &ge; 70)</div>
        </div>

        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-amber)' }}>
          <div className="card-header">
            <span className="card-title">
              <Activity size={15} color="var(--accent-amber)" /> Suspicious IPs
            </span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-amber)' }}>
            {suspiciousCount}
          </div>
          <div className="metric-sub">Tor exits, scanners, or abnormal spikes</div>
        </div>

        <div className="soc-card" style={{ borderLeft: '3px solid var(--accent-green)' }}>
          <div className="card-header">
            <span className="card-title">
              <CheckCircle size={15} color="var(--accent-green)" /> Clean / Trusted
            </span>
          </div>
          <div className="metric-value" style={{ color: 'var(--accent-green)' }}>
            {cleanCount}
          </div>
          <div className="metric-sub">Internal LAN &amp; verified public services</div>
        </div>
      </div>

      {/* ── IP Quick Lookup & Enrichment Card ─────────────────────────────────── */}
      <div className="soc-card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header" style={{ marginBottom: '0.5rem' }}>
          <span className="card-title">
            <Search size={15} color="var(--accent-cyan)" /> Single IP Live Lookup &amp; Dynamic Enrichment
          </span>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
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
            className="action-btn"
            disabled={lookupLoading || !lookupIpInput.trim()}
          >
            <Search size={14} className={lookupLoading ? 'pulse' : ''} />
            {lookupLoading ? 'Enriching...' : 'Lookup & Enrich'}
          </button>
        </form>

        {lookupError && (
          <div style={{ marginTop: '0.75rem', color: 'var(--accent-red)', fontSize: '0.85rem' }}>
            ⚠️ {lookupError}
          </div>
        )}

        {/* Detailed Lookup Result Card */}
        {lookupResult && (
          <div
            style={{
              marginTop: '1.25rem',
              padding: '1rem',
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontSize: '1.1rem', fontWeight: 'bold', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                    {lookupResult.ip}
                  </span>
                  <ReputationBadge reputation={lookupResult.reputation} />
                  {lookupResult.is_tor && (
                    <span style={{ backgroundColor: 'rgba(168, 85, 247, 0.2)', border: '1px solid var(--accent-purple)', color: 'var(--accent-purple)', fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                      Tor Exit Node
                    </span>
                  )}
                  {lookupResult.is_vpn && (
                    <span style={{ backgroundColor: 'rgba(56, 189, 248, 0.2)', border: '1px solid var(--accent-cyan)', color: 'var(--accent-cyan)', fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                      VPN / Proxy
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Source: <code>{lookupResult.source}</code> · Total Reports: {lookupResult.total_reports} · Correlated Incidents: {lookupResult.past_incidents_count}
                </div>
              </div>

              <div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Composite Threat Risk:</span>
                <RiskScoreGauge score={lookupResult.risk_score} />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', fontSize: '0.85rem' }}>
              <div>
                <strong style={{ color: 'var(--text-secondary)' }}>Geolocation:</strong>{' '}
                <span>{lookupResult.country || 'Unknown'} {lookupResult.city ? `(${lookupResult.city})` : ''}</span>
              </div>
              <div>
                <strong style={{ color: 'var(--text-secondary)' }}>ASN:</strong>{' '}
                <span className="mono-cell">{lookupResult.asn || 'N/A'}</span>
              </div>
              <div>
                <strong style={{ color: 'var(--text-secondary)' }}>ISP / Org:</strong>{' '}
                <span>{lookupResult.isp || 'N/A'}</span>
              </div>
              <div>
                <strong style={{ color: 'var(--text-secondary)' }}>Threat Tags:</strong>{' '}
                {lookupResult.threat_types && lookupResult.threat_types.length > 0 ? (
                  lookupResult.threat_types.map((tag) => (
                    <span
                      key={tag}
                      style={{
                        display: 'inline-block',
                        fontSize: '0.7rem',
                        backgroundColor: 'rgba(255, 255, 255, 0.08)',
                        padding: '1px 6px',
                        borderRadius: '3px',
                        marginRight: '4px',
                        fontFamily: 'var(--font-mono)',
                      }}
                    >
                      {tag}
                    </span>
                  ))
                ) : (
                  <span style={{ color: 'var(--text-muted)' }}>None detected</span>
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
          marginBottom: '1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Reputation:</label>
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
          <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Min Risk:</label>
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

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, minWidth: '220px' }}>
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
        <div className="alert-banner alert-error" style={{ marginBottom: '1rem' }}>
          ⚠️ {error}
        </div>
      )}

      {/* ── IP Reputation Table ─────────────────────────────────────────────── */}
      <div className="table-container">
        <table className="soc-table">
          <thead>
            <tr>
              <th style={{ minWidth: '150px' }}>IP Address</th>
              <th style={{ minWidth: '120px' }}>Reputation</th>
              <th style={{ minWidth: '120px' }}>Risk Score</th>
              <th style={{ minWidth: '130px' }}>Geolocation</th>
              <th style={{ minWidth: '160px' }}>ASN / ISP</th>
              <th style={{ minWidth: '150px' }}>Threat Tags</th>
              <th style={{ minWidth: '100px', textAlign: 'center' }}>Incidents</th>
              <th style={{ minWidth: '100px' }}>Source</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '3rem' }}>
                  <span style={{ color: 'var(--accent-cyan)' }}>Loading threat intelligence...</span>
                </td>
              </tr>
            ) : records.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: 'center', padding: '3.5rem' }}>
                  <ShieldAlert size={36} color="var(--text-muted)" style={{ marginBottom: '0.75rem' }} />
                  <div style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>No threat intelligence records found</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                    Try adjusting your search filters or click "Reset / Seed Intel" to populate threat feeds.
                  </div>
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
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 'bold',
                        color: 'var(--accent-cyan)',
                        cursor: 'pointer',
                        textAlign: 'left',
                      }}
                      title="Click to inspect full details in enrichment card"
                    >
                      {item.ip}
                    </button>
                    <div style={{ display: 'flex', gap: '4px', marginTop: '2px' }}>
                      {item.is_tor && (
                        <span style={{ fontSize: '10px', backgroundColor: 'rgba(168, 85, 247, 0.2)', color: 'var(--accent-purple)', padding: '1px 4px', borderRadius: '3px', fontWeight: 600 }}>
                          Tor
                        </span>
                      )}
                      {item.is_vpn && (
                        <span style={{ fontSize: '10px', backgroundColor: 'rgba(56, 189, 248, 0.2)', color: 'var(--accent-cyan)', padding: '1px 4px', borderRadius: '3px', fontWeight: 600 }}>
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
                      <Globe size={13} color="var(--text-muted)" />
                      <span>{item.country || 'Unknown'}</span>
                    </div>
                    {item.city && (
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{item.city}</div>
                    )}
                  </td>
                  <td>
                    <div style={{ fontSize: '0.85rem' }}>{item.isp || 'N/A'}</div>
                    {item.asn && (
                      <div className="mono-cell" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
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
                              fontSize: '0.7rem',
                              backgroundColor: 'rgba(255, 255, 255, 0.08)',
                              padding: '1px 6px',
                              borderRadius: '3px',
                              fontFamily: 'var(--font-mono)',
                            }}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>—</span>
                    )}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <span
                      style={{
                        fontWeight: item.past_incidents_count > 0 ? 'bold' : 'normal',
                        color: item.past_incidents_count > 0 ? 'var(--accent-red)' : 'var(--text-muted)',
                      }}
                    >
                      {item.past_incidents_count}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
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
      <div className="pagination-bar">
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Showing page {page} of {totalPages} ({total} total IP records)
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className="page-btn"
            disabled={page <= 1 || loading}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            <ArrowLeft size={13} style={{ marginRight: '4px' }} /> Previous
          </button>
          <button
            className="page-btn"
            disabled={page >= totalPages || loading}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next <ArrowRight size={13} style={{ marginLeft: '4px' }} />
          </button>
        </div>
      </div>
    </div>
  );
}
