/**
 * API Service for SentinelAI Frontend.
 * Communicates with FastAPI backend endpoints.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Calls GET /api/v1/health
 * Measures latency and returns the health payload.
 */
export async function fetchHealthStatus() {
  const startTime = performance.now();
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/health`, {
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

    const response = await fetch(`${API_BASE_URL}/api/v1/logs?${params.toString()}`, {
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
    const response = await fetch(`${API_BASE_URL}/api/v1/logs/seed?limit=${limit}`, {
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

    const response = await fetch(`${API_BASE_URL}/api/v1/incidents?${params.toString()}`, {
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
    const response = await fetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}`, {
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

    const response = await fetch(`${API_BASE_URL}/api/v1/incidents/${incidentId}`, {
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
    const response = await fetch(`${API_BASE_URL}/api/v1/incidents/evaluate`, {
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
