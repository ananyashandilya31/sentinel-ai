import { useEffect, useState, useCallback, useRef } from 'react';
import { liveAlertsSocket, WS_STATE } from '../services/ws';

/**
 * React hook for the real-time SOC alerts stream.
 *
 * Connects to /ws/alerts on mount and keeps the last `maxEvents`
 * live messages in state. Survives reconnects automatically.
 *
 * @param {{ maxEvents?: number }} options
 * @returns {{
 *   events: Array<object>,
 *   connectionState: string,
 *   incidentEvents: Array<object>,
 * }}
 */
export function useLiveAlerts({ maxEvents = 50 } = {}) {
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

    liveAlertsSocket.connect();

    return () => {
      unsubscribe();
      // Only tear the socket down if nothing else is subscribed
      if (liveAlertsSocket.listeners.size === 0) {
        liveAlertsSocket.disconnect();
      }
    };
  }, []);

  const incidentEvents = events.filter(
    (e) => e.type === 'NEW_INCIDENT' || e.type === 'INCIDENT_UPDATED'
  );

  return { events, connectionState, incidentEvents };
}

export default useLiveAlerts;
