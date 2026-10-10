/**
 * API Service for SentinelAI Frontend.
 * Communicates with FastAPI backend endpoints.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

/**
 * Calls the backend health endpoint GET /api/v1/health
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
