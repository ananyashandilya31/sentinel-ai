import React, { useState } from 'react';
import { Shield, LogIn, AlertTriangle, User, Lock, Info } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

/**
 * LoginPage — SOC console sign-in (Phase 8).
 *
 * Authenticates against POST /api/v1/auth/login and stores the JWT for
 * subsequent API calls.
 */
export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(err.message || 'Login failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const useDemo = () => {
    setUsername('admin');
    setPassword('admin12345');
    setError(null);
  };

  return (
    <div className="login-shell">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-brand">
          <Shield size={34} color="#38bdf8" />
          <h1 className="login-title">SENTINELAI</h1>
          <p className="login-subtitle">Security Operations Center</p>
        </div>

        {error && (
          <div className="alert-banner alert-error" style={{ marginBottom: '1rem' }}>
            <AlertTriangle size={14} /> {error}
          </div>
        )}

        <label className="login-label" htmlFor="login-username">
          Username
        </label>
        <div className="login-input-wrap">
          <User size={15} />
          <input
            id="login-username"
            className="login-input"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="admin"
            autoComplete="username"
            required
          />
        </div>

        <label className="login-label" htmlFor="login-password">
          Password
        </label>
        <div className="login-input-wrap">
          <Lock size={15} />
          <input
            id="login-password"
            className="login-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
          />
        </div>

        <button type="submit" className="login-submit" disabled={submitting}>
          <LogIn size={15} />
          {submitting ? 'Authenticating…' : 'Sign in'}
        </button>

        <button type="button" className="login-demo-hint" onClick={useDemo}>
          <Info size={12} /> Use demo credentials (admin / admin12345)
        </button>

        <p className="login-footnote">
          JWT authentication · bcrypt hashed passwords · role-based access
        </p>
      </form>
    </div>
  );
}