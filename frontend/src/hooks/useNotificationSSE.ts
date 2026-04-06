import { useState, useEffect, useRef, useCallback } from "react";

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

export interface SSENotification {
  id: string;
  type: string;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: string | null;
  created_at: string;
}

interface UseNotificationSSEResult {
  unreadCount: number;
  latestNotification: SSENotification | null;
  status: ConnectionStatus;
}

/**
 * SSE hook for live notification updates from /api/v1/notifications/stream.
 * Manages EventSource lifecycle, reconnection, and status tracking.
 * Follows the same pattern as useDashboardSSE.
 */
export function useNotificationSSE(): UseNotificationSSEResult {
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [latestNotification, setLatestNotification] =
    useState<SSENotification | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const disconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const clearDisconnectTimer = useCallback(() => {
    if (disconnectTimerRef.current) {
      clearTimeout(disconnectTimerRef.current);
      disconnectTimerRef.current = null;
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setStatus("disconnected");
      return;
    }

    const url = `/api/v1/notifications/stream?token=${encodeURIComponent(token)}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;

    es.onopen = () => {
      clearDisconnectTimer();
      setStatus("connected");
    };

    es.addEventListener("unread_count", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as { count: number };
        setUnreadCount(data.count);
      } catch {
        // Ignore malformed SSE data
      }
    });

    es.addEventListener("new_notification", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data) as SSENotification;
        setLatestNotification(data);
      } catch {
        // Ignore malformed SSE data
      }
    });

    es.onerror = () => {
      setStatus("reconnecting");
      clearDisconnectTimer();

      // If disconnected for >30 seconds, mark as disconnected
      disconnectTimerRef.current = setTimeout(() => {
        setStatus("disconnected");
      }, 30_000);
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
      clearDisconnectTimer();
    };
  }, [clearDisconnectTimer]);

  return { unreadCount, latestNotification, status };
}
