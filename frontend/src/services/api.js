/**
 * API Service for SentinelAI Frontend.
 * Communicates with FastAPI backend endpoints.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/**
 * authFetch — fetch wrapper that attaches the stored JWT as a Bearer
 * token (Phase 8) and redirects to the login screen on 401.
 *
 * All API helpers below go through this so protected write endpoints
 * work without threading the token through every call site.
 */
async function authFetch(url, options = {}) {
  const token = localStorage.getItem('sentinelai_token');
  const headers = { Accept: 'application/json', ...(options.headers || {}) };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401 && token) {
    // Token expired or revoked — drop it so the app shows the login screen
    localStorage.removeItem('sentinelai_token');
    localStorage.removeItem('sentinelai_user');
  }

  return response;
}

/**
 * Calls GET /api/v1/health
 * Measures latency and returns the health payload.
 */
export async function fetchHealthStatus() {
  const startTime = performance.now();
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/health`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    const latencyMs = Math.round(performance.now() - startTime);

    if (!response.ok) {
      return {
        success: false,
        status: 'error',
        httpStatus: response.status,
        latencyMs,
        error: `Server responded with status HTTP ${response.status}`,
      };
    }

    const data = await response.json();
    return {
      success: true,
      latencyMs,
      data,
    };
  } catch (error) {
    const latencyMs = Math.round(performance.now() - startTime);
    return {
      success: false,
      status: 'offline',
      latencyMs,
      error: error.message || 'Network error / backend unreachable',
    };
  }
}

/**
 * Calls GET /api/v1/logs with optional search, filters, and pagination.
 */
export async function fetchLogs({
  page = 1,
  pageSize = 20,
  user = '',
  ip = '',
  eventType = '',
  search = '',
} = {}) {
  try {
    const params = new URLSearchParams();
    params.set('page', page);
    params.set('page_size', pageSize);
    if (user) params.set('user', user);
    if (ip) params.set('ip', ip);
    if (eventType) params.set('event_type', eventType);
    if (search) params.set('search', search);

    const response = await authFetch(`${API_BASE_URL}/api/v1/logs?${params.toString()}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch logs (HTTP ${response.status})`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching security logs:', error);
    throw error;
  }
}

/**
 * Calls POST /api/v1/logs/seed to populate the database with synthetic logs.
 */
export async function seedLogs(limit = 250) {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/logs/seed?limit=${limit}`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to seed logs (HTTP ${response.status})`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error seeding logs:', error);
    throw error;
  }
}

/**
 * Calls GET /api/v1/incidents
 */
export async function fetchIncidents({
  page = 1,
  pageSize = 20,
  severity = '',
  status = '',
  type = '',
} = {}) {
  try {
    const params = new URLSearchParams();
    params.set('page', page);
    params.set('page_size', pageSize);
    if (severity) params.set('severity', severity);
    if (status) params.set('status', status);
    if (type) params.set('type', type);

    const response = await authFetch(`${API_BASE_URL}/api/v1/incidents?${params.toString()}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch incidents (HTTP ${response.status})`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching incidents:', error);
    throw error;
  }
}

/**
 * Calls GET /api/v1/incidents/{id}
 */
export async function fetchIncidentById(incidentId) {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch incident ${incidentId} (HTTP ${response.status})`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching incident detail:', error);
    throw error;
  }
}

/**
 * Calls PATCH /api/v1/incidents/{id}
 */
export async function updateIncidentStatus(incidentId, { status, assigned_to }) {
  try {
    const payload = {};
    if (status) payload.status = status;
    if (assigned_to !== undefined) payload.assigned_to = assigned_to;

    const response = await authFetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`Failed to update incident (HTTP ${response.status})`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error updating incident:', error);
    throw error;
  }
}

/**
 * Calls POST /api/v1/incidents/evaluate to manually trigger rule evaluation
 */
export async function evaluateDetection() {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/incidents/evaluate`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to execute detection engine (HTTP ${response.status})`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error triggering detection:', error);
    throw error;
  }
}

// ─── ML Anomaly Detection ──────────────────────────────────────────────────

/**
 * Calls POST /api/v1/ml/train — trains the Isolation Forest model.
 */
export async function trainModel() {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/ml/train`, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error training model:', error);
    throw error;
  }
}

/**
 * Calls GET /api/v1/ml/status — checks whether the model is ready.
 */
export async function fetchMLStatus() {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/ml/status`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching ML status:', error);
    throw error;
  }
}

/**
 * Calls POST /api/v1/ml/predict — scores logs from the last N hours.
 */
export async function runMLPredict(hours = 24) {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/ml/predict?hours=${hours}`, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error running ML predict:', error);
    throw error;
  }
}

/**
 * Calls GET /api/v1/ml/predictions — paginated list of stored predictions.
 */
export async function fetchMLPredictions({
  page = 1,
  pageSize = 20,
  anomaliesOnly = false,
} = {}) {
  try {
    const params = new URLSearchParams();
    params.set('page', page);
    params.set('page_size', pageSize);
    if (anomaliesOnly) params.set('anomalies_only', 'true');

    const response = await authFetch(`${API_BASE_URL}/api/v1/ml/predictions?${params.toString()}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch ML predictions (HTTP ${response.status})`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching ML predictions:', error);
    throw error;
  }
}

/**
 * Calls GET /api/v1/threat-intel with pagination, filters, and search.
 */
export async function fetchThreatIntel({
  page = 1,
  pageSize = 20,
  reputation = '',
  minRisk = '',
  search = '',
} = {}) {
  try {
    const params = new URLSearchParams();
    params.set('page', page);
    params.set('page_size', pageSize);
    if (reputation) params.set('reputation', reputation);
    if (minRisk !== '' && minRisk !== null) params.set('min_risk', minRisk);
    if (search) params.set('search', search);

    const response = await authFetch(`${API_BASE_URL}/api/v1/threat-intel?${params.toString()}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch threat intel (HTTP ${response.status})`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching threat intel:', error);
    throw error;
  }
}

/**
 * Calls GET /api/v1/threat-intel/{ip} for single IP lookup & dynamic enrichment.
 */
export async function lookupIPReputation(ip) {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/threat-intel/${encodeURIComponent(ip)}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Error looking up IP ${ip}:`, error);
    throw error;
  }
}

/**
 * Calls POST /api/v1/threat-intel/seed to seed threat intelligence database.
 */
export async function seedThreatIntel(overwrite = false) {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/threat-intel/seed?overwrite=${overwrite}`, {
      method: 'POST',
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to seed threat intel (HTTP ${response.status})`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error seeding threat intel:', error);
    throw error;
  }
}

/**
 * Calls GET /api/v1/threat-intel/incident/{incidentId}
 */
export async function fetchIncidentThreatIntel(incidentId) {
  try {
    const response = await authFetch(`${API_BASE_URL}/api/v1/threat-intel/incident/${incidentId}`, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch incident threat intel (HTTP ${response.status})`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Error fetching incident threat intel for ${incidentId}:`, error);
    throw error;
  }
}

/**
 * Calls POST /api/v1/incidents/{incidentId}/investigate
 * Triggers AI incident investigation and analysis.
 */
export async function triggerInvestigation(incidentId, forceRefresh = false) {
  try {
    const response = await authFetch(
      `${API_BASE_URL}/api/v1/incidents/${incidentId}/investigate?force_refresh=${forceRefresh}`,
      {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
      }
    );
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Error triggering investigation for ${incidentId}:`, error);
    throw error;
  }
}

/**
 * Calls GET /api/v1/incidents/{incidentId}/investigation
 */
export async function fetchInvestigation(incidentId) {
  try {
    const response = await authFetch(
      `${API_BASE_URL}/api/v1/incidents/${incidentId}/investigation`,
      {
        method: 'GET',
        headers: { 'Accept': 'application/json' },
      }
    );
    if (!response.ok) {
      if (response.status === 404) return null;
      throw new Error(`HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`Error fetching investigation for ${incidentId}:`, error);
    throw error;
  }
}
