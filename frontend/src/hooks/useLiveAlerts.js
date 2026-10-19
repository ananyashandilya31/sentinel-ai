import { useEffect, useState, useCallback, useRef } from 'react';
import { liveAlertsSocket, WS_STATE } from '../services/ws';
import { useAuth } from '../context/AuthContext';

/**
 * React hook for the real-time SOC alerts stream.
 *
 * Connects to /ws/alerts on mount and keeps the last `maxEvents`
 * live messages in state. Survives reconnects automatically.
 *
 * The socket is (re)opened whenever the authentication state changes,
 * so a rejected token (close code 1008) recovers after a fresh login.
 *
 * @param {{ maxEvents?: number }} options
 * @returns {{
 *   events: Array<object>,
 *   connectionState: string,
 *   incidentEvents: Array<object>,
 *   isLive: boolean,
 * }}
 */
export function useLiveAlerts({ maxEvents = 50 } = {}) {
  const { isAuthenticated } = useAuth();
  const [events, setEvents] = useState([]);
  const [connectionState, setConnectionState] = useState(
    liveAlertsSocket.state
  );
  const maxEventsRef = useRef(maxEvents);
  maxEventsRef.current = maxEvents;

  useEffect(() => {
    const unsubscribe = liveAlertsSocket.subscribe((message) => {
      if (!message || typeof message !== 'object') return;

      if (message.type === 'CONNECTION_STATE') {
        setConnectionState(message.state);
        return;
      }

      setEvents((prev) => {
        const next = [message, ...prev];
        return next.slice(0, maxEventsRef.current);
      });
    });

    if (isAuthenticated) {
      liveAlertsSocket.connect();
    }

    return () => {
      unsubscribe();
      // Only tear the socket down if nothing else is subscribed
      if (liveAlertsSocket.listeners.size === 0) {
        liveAlertsSocket.disconnect();
      }
    };
  }, [isAuthenticated]);

  const incidentEvents = events.filter(
    (e) => e.type === 'NEW_INCIDENT' || e.type === 'INCIDENT_UPDATED'
  );

  const isLive = connectionState === WS_STATE.OPEN;

  return { events, connectionState, incidentEvents, isLive };
}

export default useLiveAlerts;
