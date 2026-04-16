import { useEffect, useRef, useState, useCallback } from "react";

/** Shape of an event received from the SSE stream. */
export interface EventStreamEvent {
  event_type: string;
  data: Record<string, unknown>;
  timestamp: string;
  project_id: string | null;
  tenant_id: string | null;
}

/** Return value of the `useEventStream` hook. */
export interface UseEventStreamReturn {
  connected: boolean;
  reconnecting: boolean;
  subscriberCount: number;
}

const MAX_BACKOFF_MS = 30_000;
const INITIAL_BACKOFF_MS = 1_000;

/**
 * Custom hook that connects to the SSE event stream and invokes `onEvent`
 * whenever a matching server-sent event arrives.
 *
 * - Auto-reconnects with exponential backoff (1 s → 2 s → 4 s … max 30 s).
 * - Cleans up the `EventSource` on unmount.
 */
export function useEventStream(
  eventTypes: string[],
  onEvent: (event: EventStreamEvent) => void,
): UseEventStreamReturn {
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [subscriberCount, setSubscriberCount] = useState(0);

  // Keep a stable reference to the latest callback so reconnects don't
  // create stale closures.
  const onEventRef = useRef(onEvent);
  useEffect(() => {
    onEventRef.current = onEvent;
  });

  // Stable ref for event types to avoid re-triggering effect on every render
  const eventTypesKey = eventTypes.join(",");

  const connect = useCallback(() => {
    const params = eventTypesKey ? `?event_types=${encodeURIComponent(eventTypesKey)}` : "";
    const url = `/api/events/stream${params}`;
    return new EventSource(url);
  }, [eventTypesKey]);

  useEffect(() => {
    let es: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    let backoff = INITIAL_BACKOFF_MS;
    let cancelled = false;

    function open() {
      if (cancelled) return;

      es = connect();

      es.onopen = () => {
        setConnected(true);
        setReconnecting(false);
        backoff = INITIAL_BACKOFF_MS;

        // Fetch subscriber count after connecting
        fetch("/api/events/stream/health")
          .then((r) => r.json())
          .then((d: { subscriber_count?: number }) => {
            if (!cancelled) setSubscriberCount(d.subscriber_count ?? 0);
          })
          .catch(() => {
            /* health endpoint may not be available yet */
          });
      };

      // Listen for each requested event type individually so the browser
      // dispatches by event name rather than the generic "message" event.
      const types = eventTypesKey ? eventTypesKey.split(",") : [];
      for (const eventType of types) {
        es.addEventListener(eventType, ((evt: MessageEvent) => {
          try {
            const parsed: EventStreamEvent = JSON.parse(evt.data);
            onEventRef.current(parsed);
          } catch {
            /* ignore malformed messages */
          }
        }) as EventListener);
      }

      // Also handle generic "message" events (unnamed events)
      if (types.length === 0) {
        es.onmessage = (evt: MessageEvent) => {
          try {
            const parsed: EventStreamEvent = JSON.parse(evt.data);
            onEventRef.current(parsed);
          } catch {
            /* ignore malformed messages */
          }
        };
      }

      es.onerror = () => {
        setConnected(false);
        es?.close();
        es = null;

        if (cancelled) return;

        setReconnecting(true);
        retryTimeout = setTimeout(() => {
          backoff = Math.min(backoff * 2, MAX_BACKOFF_MS);
          open();
        }, backoff);
      };
    }

    open();

    return () => {
      cancelled = true;
      if (retryTimeout) clearTimeout(retryTimeout);
      if (es) {
        es.close();
        es = null;
      }
      setConnected(false);
      setReconnecting(false);
    };
  }, [connect, eventTypesKey]);

  return { connected, reconnecting, subscriberCount };
}
