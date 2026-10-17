/**
 * Authentication service for the SentinelAI SOC console.
 *
 * The JWT is kept in localStorage so a page refresh keeps the analyst
 * signed in, and sent as a Bearer token on every API call (see the
 * authFetch helper injected into api.js).
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const TOKEN_KEY = 'sentinelai_token';
const USER_KEY = 'sentinelai_user';

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function storeSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/**
 * Calls POST /api/v1/auth/login
 */
export async function login(username, password) {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || `Login failed (HTTP ${response.status})`);
  }

  storeSession(data.access_token, data.user);
  return data;
}

/**
 * Calls GET /api/v1/auth/me — validates the stored token on app start.
 */
export async function fetchCurrentUser() {
  const token = getStoredToken();
  if (!token) return null;

  const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
  });

  if (!response.ok) {
    clearSession();
    return null;
  }

  const user = await response.json();
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}

/**
 * Calls POST /api/v1/auth/register (admin only).
 */
export async function registerUser({ username, password, role = 'ANALYST', email = null }) {
  const token = getStoredToken();
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ username, password, role, email }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `Registration failed (HTTP ${response.status})`);
  }
  return data;
}