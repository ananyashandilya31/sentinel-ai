import React, { useState, useEffect, useCallback } from 'react';
import { BrainCircuit, RefreshCw, Play, Cpu } from 'lucide-react';
import AnomalyScoreBadge from '../components/AnomalyScoreBadge';
import { trainModel, fetchMLStatus, fetchMLPredictions, runMLPredict } from '../services/api';

export default function MLPredictionsPage() {
  const [predictions, setPredictions] = useState([]);
  const [total, setTotal] = useState(0);
  const [anomaliesCount, setAnomaliesCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [anomaliesOnly, setAnomaliesOnly] = useState(false);
  const [modelReady, setModelReady] = useState(false);
  const [modelMessage, setModelMessage] = useState('Checking model status…');
  const [loading, setLoading] = useState(false);
  const [training, setTraining] = useState(false);
  const [predicting, setPredicting] = useState(false);
  const [trainMetrics, setTrainMetrics] = useState(null);
  const [error, setError] = useState(null);

  // ─── Status check ────────────────────────────────────────────────────────────
  const checkStatus = useCallback(async () => {
    try {
      const status = await fetchMLStatus();
      setModelReady(status.model_ready);
      setModelMessage(status.message);
    } catch {
      setModelReady(false);
      setModelMessage('Unable to reach backend.');
    }
  }, []);

  // ─── Load predictions ────────────────────────────────────────────────────────
  const loadPredictions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMLPredictions({ page, pageSize, anomaliesOnly });
      setPredictions(data.predictions || []);
      setTotal(data.total || 0);
      setAnomaliesCount(data.anomalies_count || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, anomaliesOnly]);

  useEffect(() => {
    checkStatus();
    loadPredictions();
  }, [checkStatus, loadPredictions]);

  // ─── Train ───────────────────────────────────────────────────────────────────
  const handleTrain = async () => {
    setTraining(true);
    setError(null);
    setTrainMetrics(null);
    try {
      const result = await trainModel();
      setTrainMetrics(result);
      setModelReady(true);
      setModelMessage('Model ready — call POST /ml/predict to score logs.');
    } catch (err) {
      setError(`Training failed: ${err.message}`);
    } finally {
      setTraining(false);
    }
  };

  // ─── Score logs ──────────────────────────────────────────────────────────────
  const handlePredict = async () => {
    setPredicting(true);
    setError(null);
    try {
      await runMLPredict(24);
      await loadPredictions();
    } catch (err) {
      setError(`Scoring failed: ${err.message}`);
    } finally {
      setPredicting(false);
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div>
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="phase-banner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div>
            <div className="phase-title">ML Anomaly Detection</div>
            <div className="phase-description">
              Unsupervised Isolation Forest behavioural anomaly scoring and feature inference.
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          {/* Model status pill */}
          <span
            className={`system-status-pill ${modelReady ? 'badge-connected' : 'badge-disconnected'}`}
            style={{ fontSize: '0.7rem' }}
          >
            <span
              className={`status-indicator ${modelReady ? 'pulse' : ''}`}
              style={{ backgroundColor: modelReady ? 'var(--accent-green)' : 'var(--accent-red)' }}
            />
            {modelReady ? 'MODEL READY' : 'NO MODEL'}
          </span>

          <button
            className="btn-secondary"
            onClick={handleTrain}
            disabled={training}
            title="Train or retrain the Isolation Forest model"
          >
            <Cpu size={14} />
            {training ? 'Training…' : 'Train Model'}
          </button>

          <button
            className="btn-primary"
            onClick={handlePredict}
            disabled={predicting || !modelReady}
            title="Score logs from the last 24 hours"
          >
            <Play size={14} />
            {predicting ? 'Scoring…' : 'Score Logs (24h)'}
          </button>

          <button className="btn-secondary" onClick={loadPredictions} disabled={loading}>
            <RefreshCw size={14} className={loading ? 'spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* ── Error banner ───────────────────────────────────────────────────── */}
      {error && (
        <div className="alert-banner alert-error" style={{ marginBottom: '1rem' }}>
          ⚠ {error}
        </div>
      )}

      {/* ── Train metrics card ─────────────────────────────────────────────── */}
      {trainMetrics && (
        <div className="detail-card" style={{ marginBottom: '1.25rem' }}>
          <div className="detail-section-title" style={{ marginBottom: '0.75rem' }}>
            📊 Training Results
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
            {[
              { label: 'Precision', value: (trainMetrics.precision * 100).toFixed(1) + '%' },
              { label: 'Recall', value: (trainMetrics.recall * 100).toFixed(1) + '%' },
              { label: 'F1 Score', value: (trainMetrics.f1 * 100).toFixed(1) + '%' },
              { label: 'ROC-AUC', value: trainMetrics.roc_auc.toFixed(3) },
            ].map(({ label, value }) => (
              <div key={label} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                  {value}
                </div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {label}
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            Trained on {trainMetrics.n_samples} IPs · {trainMetrics.n_attack_ips} attack IPs ·{' '}
            {trainMetrics.n_normal_ips} normal IPs
          </div>
        </div>
      )}

      {/* ── Metrics row ────────────────────────────────────────────────────── */}
      <div className="metrics-row" style={{ marginBottom: '1.25rem' }}>
        {[
          { label: 'Total Predictions', value: total, color: 'var(--accent-blue)' },
          { label: 'Anomalies Detected', value: anomaliesCount, color: 'var(--accent-red)' },
          {
            label: 'Normal IPs',
            value: total - anomaliesCount,
            color: 'var(--accent-green)',
          },
          {
            label: 'Anomaly Rate',
            value: total > 0 ? ((anomaliesCount / total) * 100).toFixed(1) + '%' : '—',
            color: 'var(--accent-amber)',
          },
        ].map(({ label, value, color }) => (
          <div key={label} className="metric-card">
            <div className="metric-value" style={{ color }}>
              {value}
            </div>
            <div className="metric-label">{label}</div>
          </div>
        ))}
      </div>

      {/* ── Filter bar ─────────────────────────────────────────────────────── */}
      <div className="filter-bar" style={{ marginBottom: '1rem' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={anomaliesOnly}
            onChange={(e) => { setAnomaliesOnly(e.target.checked); setPage(1); }}
            style={{ accentColor: 'var(--accent-red)' }}
          />
          Show anomalies only
        </label>
      </div>

      {/* ── Predictions table ──────────────────────────────────────────────── */}
      {!modelReady && predictions.length === 0 ? (
        <div className="empty-state">
          <BrainCircuit size={40} color="var(--text-muted)" />
          <p style={{ marginTop: '1rem' }}>No model trained yet.</p>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Click <strong>Train Model</strong> to train the Isolation Forest, then{' '}
            <strong>Score Logs</strong> to detect anomalies.
          </p>
        </div>
      ) : loading ? (
        <div className="empty-state">Loading predictions…</div>
      ) : predictions.length === 0 ? (
        <div className="empty-state">
          <p>No predictions stored yet.</p>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Click <strong>Score Logs (24h)</strong> to run the model.
          </p>
        </div>
      ) : (
        <>
          <div className="table-container">
            <table className="soc-table">
            <thead>
              <tr>
                <th>IP Address</th>
                <th>Anomaly Score</th>
                <th>Verdict</th>
                <th>Failed Logins</th>
                <th>Unique Ports</th>
                <th>Data (MB)</th>
                <th>Event Count</th>
                <th>Evaluated At</th>
              </tr>
            </thead>
            <tbody>
              {predictions.map((pred) => (
                <tr key={pred.id} style={pred.is_anomaly ? { background: 'rgba(239,68,68,0.05)' } : {}}>
                  <td>
                    <code style={{ fontSize: '0.78rem', color: 'var(--accent-blue)' }}>
                      {pred.ip}
                    </code>
                  </td>
                  <td>
                    <AnomalyScoreBadge score={pred.anomaly_score} />
                  </td>
                  <td>
                    <span
                      className={`severity-badge ${pred.is_anomaly ? 'badge-critical' : 'badge-low'}`}
                    >
                      {pred.is_anomaly ? '🚨 ANOMALY' : '✓ NORMAL'}
                    </span>
                  </td>
                  <td>{pred.feature_vector?.failed_login_count ?? '—'}</td>
                  <td>{pred.feature_vector?.unique_ports ?? '—'}</td>
                  <td>{pred.feature_vector?.data_transfer_mb ?? '—'}</td>
                  <td>{pred.feature_vector?.event_count ?? '—'}</td>
                  <td style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    {new Date(pred.evaluated_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination-row">
              <button
                className="btn-secondary"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                ← Prev
              </button>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Page {page} / {totalPages}
              </span>
              <button
                className="btn-secondary"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
