import { useState, useEffect, useRef, useCallback } from 'react';
import type { KpiMetrics } from '../api/dashboard';

type ConnectionStatus = 'connected' | 'reconnecting' | 'disconnected';

interface UseDashboardSSEResult {
  metrics: KpiMetrics | null;
  status: ConnectionStatus;
}

/**
 * SSE hook for live KPI updates from the dashboard stream endpoint.
 * Manages EventSource lifecycle, reconnection, and status tracking.
 */
export function useDashboardSSE(templateId?: string): UseDashboardSSEResult {
  const [metrics, setMetrics] = useState<KpiMetrics | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const disconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const clearDisconnectTimer = useCallback(() => {
    if (disconnectTimerRef.current) {
      clearTimeout(disconnectTimerRef.current);
      disconnectTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setStatus('disconnected');
      return;
    }

    // Build SSE URL with token as query param (per RESEARCH.md Pitfall 3)
    let url = `/api/v1/dashboard/stream?token=${encodeURIComponent(token)}`;
    if (templateId) {
      url += `&template_id=${encodeURIComponent(templateId)}`;
    }

    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      clearDisconnectTimer();
      setStatus('connected');
    };

    es.addEventListener('kpi_update', (event: MessageEvent) => {
      try {
        const data: KpiMetrics = JSON.parse(event.data);
        setMetrics(data);
      } catch {
        // Ignore malformed SSE data
      }
    });

    es.onerror = () => {
      setStatus('reconnecting');
      clearDisconnectTimer();

      // If disconnected for >30 seconds, mark as disconnected
      disconnectTimerRef.current = setTimeout(() => {
        setStatus('disconnected');
      }, 30_000);
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
      clearDisconnectTimer();
    };
  }, [templateId, clearDisconnectTimer]);

  return { metrics, status };
}
