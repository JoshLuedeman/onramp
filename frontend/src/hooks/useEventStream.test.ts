import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useEventStream } from "./useEventStream";
import type { EventStreamEvent } from "./useEventStream";

// ---------------------------------------------------------------------------
// EventSource mock
// ---------------------------------------------------------------------------

type ESListener = (evt: MessageEvent) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];

  url: string;
  readyState: number;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((evt: MessageEvent) => void) | null = null;

  private listeners: Record<string, ESListener[]> = {};

  constructor(url: string) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    MockEventSource.instances.push(this);

    // Simulate async open
    setTimeout(() => {
      this.readyState = 1; // OPEN
      this.onopen?.();
    }, 0);
  }

  addEventListener(type: string, listener: ESListener) {
    if (!this.listeners[type]) this.listeners[type] = [];
    this.listeners[type].push(listener);
  }

  removeEventListener(type: string, listener: ESListener) {
    const arr = this.listeners[type];
    if (arr) {
      this.listeners[type] = arr.filter((l) => l !== listener);
    }
  }

  dispatchEvent(type: string, data: string) {
    const evt = new MessageEvent(type, { data });
    for (const l of this.listeners[type] ?? []) {
      l(evt);
    }
    if (type === "message" && this.onmessage) {
      this.onmessage(evt);
    }
  }

  close() {
    this.readyState = 2; // CLOSED
  }

  // Helper: simulate a server error
  simulateError() {
    this.readyState = 2;
    this.onerror?.();
  }
}

// ---------------------------------------------------------------------------
// Test setup
// ---------------------------------------------------------------------------

describe("useEventStream", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
    vi.useFakeTimers({ shouldAdvanceTime: true });

    // Mock the health endpoint fetch
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        json: () => Promise.resolve({ subscriber_count: 5 }),
      }),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("connects to the SSE endpoint with event types", async () => {
    const onEvent = vi.fn();
    renderHook(() => useEventStream(["drift_detected", "scan_started"], onEvent));

    // Let the async open fire
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toBe(
      "/api/events/stream?event_types=drift_detected%2Cscan_started",
    );
  });

  it("calls onEvent callback when events arrive", async () => {
    const onEvent = vi.fn();
    renderHook(() => useEventStream(["drift_detected"], onEvent));

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });

    const es = MockEventSource.instances[0];

    const payload: EventStreamEvent = {
      event_type: "drift_detected",
      data: { resource: "vnet-01" },
      timestamp: "2025-01-01T00:00:00Z",
      project_id: null,
      tenant_id: null,
    };

    act(() => {
      es.dispatchEvent("drift_detected", JSON.stringify(payload));
    });

    expect(onEvent).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledWith(payload);
  });

  it("sets connected to true after open", async () => {
    const onEvent = vi.fn();
    const { result } = renderHook(() =>
      useEventStream(["scan_started"], onEvent),
    );

    expect(result.current.connected).toBe(false);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(result.current.connected).toBe(true);
    expect(result.current.reconnecting).toBe(false);
  });

  it("auto-reconnects on disconnect with exponential backoff", async () => {
    const onEvent = vi.fn();
    const { result } = renderHook(() =>
      useEventStream(["scan_started"], onEvent),
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(result.current.connected).toBe(true);

    // Simulate error → disconnect
    act(() => {
      MockEventSource.instances[0].simulateError();
    });

    expect(result.current.connected).toBe(false);
    expect(result.current.reconnecting).toBe(true);

    // After 1 s backoff a new EventSource should be created
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });

    expect(MockEventSource.instances).toHaveLength(2);

    // Open the second one
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(result.current.connected).toBe(true);
    expect(result.current.reconnecting).toBe(false);
  });

  it("cleans up EventSource on unmount", async () => {
    const onEvent = vi.fn();
    const { unmount } = renderHook(() =>
      useEventStream(["scan_started"], onEvent),
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });

    const es = MockEventSource.instances[0];
    expect(es.readyState).toBe(1); // OPEN

    unmount();

    expect(es.readyState).toBe(2); // CLOSED
  });

  it("fetches subscriber count on connect", async () => {
    const onEvent = vi.fn();
    const { result } = renderHook(() =>
      useEventStream(["scan_started"], onEvent),
    );

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });

    // Allow the fetch promise to resolve
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });

    expect(result.current.subscriberCount).toBe(5);
  });
});
