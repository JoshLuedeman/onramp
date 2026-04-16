import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useStreamingChat } from "./useStreamingChat";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build an SSE text payload from typed events. */
function ssePayload(
  events: Array<{ event: string; data: Record<string, unknown> }>,
): string {
  return events
    .map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`)
    .join("");
}

/** Create a ReadableStream from a string. */
function stringStream(text: string): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(text));
      controller.close();
    },
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useStreamingChat", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  // 1 — Initial state
  it("starts in idle state with no content", () => {
    const { result } = renderHook(() => useStreamingChat("conv-1"));

    expect(result.current.state).toBe("idle");
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.partialContent).toBe("");
    expect(result.current.fullContent).toBe("");
    expect(result.current.retryCount).toBe(0);
  });

  // 2 — Successful streaming with data + done events
  it("streams content and transitions idle → streaming → complete", async () => {
    const payload = ssePayload([
      { event: "status", data: { status: "started" } },
      { event: "data", data: { token: "Hello " } },
      { event: "data", data: { token: "world" } },
      { event: "done", data: { full_text: "Hello world" } },
    ]);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: stringStream(payload),
    });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      await result.current.streamMessage("Hi");
    });

    expect(result.current.state).toBe("complete");
    expect(result.current.fullContent).toBe("Hello world");
    expect(result.current.partialContent).toBe("Hello world");
    expect(result.current.isStreaming).toBe(false);
  });

  // 3 — Partial content accumulates during streaming
  it("accumulates partial content from data events", async () => {
    const payload = ssePayload([
      { event: "status", data: { status: "started" } },
      { event: "data", data: { token: "one " } },
      { event: "data", data: { token: "two " } },
      { event: "data", data: { token: "three" } },
      { event: "done", data: { full_text: "one two three" } },
    ]);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: stringStream(payload),
    });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      await result.current.streamMessage("test");
    });

    expect(result.current.partialContent).toBe("one two three");
  });

  // 4 — Non-retryable error transitions to error state
  it("transitions to error state on non-retryable stream error", async () => {
    const payload = ssePayload([
      { event: "status", data: { status: "started" } },
      { event: "data", data: { token: "partial " } },
      {
        event: "error",
        data: {
          code: "RATE_LIMIT",
          message: "Rate limited",
          retryable: false,
        },
      },
      { event: "done", data: { full_text: "partial " } },
    ]);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: stringStream(payload),
    });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      await result.current.streamMessage("test");
    });

    expect(result.current.state).toBe("error");
    expect(result.current.error).not.toBeNull();
    expect(result.current.error!.code).toBe("RATE_LIMIT");
    expect(result.current.error!.retryable).toBe(false);
  });

  // 5 — Partial content preserved after error
  it("preserves partial content when stream errors", async () => {
    const payload = ssePayload([
      { event: "status", data: { status: "started" } },
      { event: "data", data: { token: "saved " } },
      { event: "data", data: { token: "content" } },
      {
        event: "error",
        data: {
          code: "INTERNAL",
          message: "Server error",
          retryable: false,
        },
      },
      { event: "done", data: { full_text: "" } },
    ]);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: stringStream(payload),
    });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      await result.current.streamMessage("test");
    });

    // Partial content should be preserved even after error
    expect(result.current.partialContent).toBe("saved content");
    expect(result.current.state).toBe("error");
  });

  // 6 — Retries on retryable error with backoff
  it("retries on retryable error up to max retries", async () => {
    // First attempt: retryable error
    const errorPayload = ssePayload([
      { event: "status", data: { status: "started" } },
      {
        event: "error",
        data: {
          code: "STREAM_ERROR",
          message: "timeout occurred",
          retryable: true,
        },
      },
      { event: "done", data: { full_text: "" } },
    ]);

    // Second attempt: success
    const successPayload = ssePayload([
      { event: "status", data: { status: "started" } },
      { event: "data", data: { token: "recovered" } },
      { event: "done", data: { full_text: "recovered" } },
    ]);

    fetchMock
      .mockResolvedValueOnce({ ok: true, body: stringStream(errorPayload) })
      .mockResolvedValueOnce({
        ok: true,
        body: stringStream(successPayload),
      });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      const promise = result.current.streamMessage("test");
      // Advance past the first backoff (1000ms)
      await vi.advanceTimersByTimeAsync(1_500);
      await promise;
    });

    expect(result.current.state).toBe("complete");
    expect(result.current.fullContent).toBe("recovered");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  // 7 — Stops retrying after max retries
  it("stops retrying after MAX_RETRIES and stays in error", async () => {
    const errorPayload = ssePayload([
      { event: "status", data: { status: "started" } },
      {
        event: "error",
        data: {
          code: "STREAM_ERROR",
          message: "timeout error",
          retryable: true,
        },
      },
      { event: "done", data: { full_text: "" } },
    ]);

    // Mock 4 calls (initial + 3 retries)
    fetchMock
      .mockResolvedValueOnce({ ok: true, body: stringStream(errorPayload) })
      .mockResolvedValueOnce({ ok: true, body: stringStream(errorPayload) })
      .mockResolvedValueOnce({ ok: true, body: stringStream(errorPayload) })
      .mockResolvedValueOnce({ ok: true, body: stringStream(errorPayload) });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      const promise = result.current.streamMessage("test");
      // Advance through all backoffs: 1s + 2s + 4s
      await vi.advanceTimersByTimeAsync(8_000);
      await promise;
    });

    expect(result.current.state).toBe("error");
    // Should have called fetch 4 times (initial + 3 retries)
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });

  // 8 — HTTP error response
  it("sets error on HTTP error response", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      await result.current.streamMessage("test");
    });

    expect(result.current.state).toBe("error");
    expect(result.current.error!.code).toBe("CONNECTION_ERROR");
    expect(result.current.error!.message).toContain("500");
  });

  // 9 — Cancel aborts the stream
  it("cancel aborts the stream and resets to idle", async () => {
    // Create a stream that won't end on its own
    const neverEndingStream = new ReadableStream<Uint8Array>({
      start() {
        // Never closes
      },
    });

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: neverEndingStream,
    });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    // Start streaming (non-blocking since it won't complete)
    act(() => {
      result.current.streamMessage("test");
    });

    // Allow the fetch to resolve and streaming to start
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });

    // Cancel the stream
    act(() => {
      result.current.cancel();
    });

    expect(result.current.state).toBe("idle");
  });

  // 10 — Sends correct request format
  it("sends POST request with correct body and headers", async () => {
    const payload = ssePayload([
      { event: "status", data: { status: "started" } },
      { event: "done", data: { full_text: "" } },
    ]);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: stringStream(payload),
    });

    const { result } = renderHook(() => useStreamingChat("my-conv-id"));

    await act(async () => {
      await result.current.streamMessage("Hello architect");
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat/my-conv-id/stream",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: "Hello architect" }),
      }),
    );
  });

  // 11 — Network error triggers retry
  it("retries on network fetch error", async () => {
    // First call: network error
    fetchMock.mockRejectedValueOnce(new Error("network error: connection reset"));

    // Second call: success
    const successPayload = ssePayload([
      { event: "status", data: { status: "started" } },
      { event: "data", data: { token: "ok" } },
      { event: "done", data: { full_text: "ok" } },
    ]);
    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: stringStream(successPayload),
    });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      const promise = result.current.streamMessage("test");
      await vi.advanceTimersByTimeAsync(1_500);
      await promise;
    });

    expect(result.current.state).toBe("complete");
    expect(result.current.fullContent).toBe("ok");
  });

  // 12 — Stream ending without done event uses accumulated content
  it("completes with accumulated content when stream ends without done event", async () => {
    const payload = ssePayload([
      { event: "status", data: { status: "started" } },
      { event: "data", data: { token: "fallback " } },
      { event: "data", data: { token: "content" } },
    ]);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: stringStream(payload),
    });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      await result.current.streamMessage("test");
    });

    expect(result.current.state).toBe("complete");
    expect(result.current.fullContent).toBe("fallback content");
  });

  // 13 — Status event is handled without error
  it("handles status events without crashing", async () => {
    const payload = ssePayload([
      { event: "status", data: { status: "started" } },
      { event: "status", data: { status: "processing" } },
      { event: "data", data: { token: "ok" } },
      { event: "done", data: { full_text: "ok" } },
    ]);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: stringStream(payload),
    });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      await result.current.streamMessage("test");
    });

    expect(result.current.state).toBe("complete");
    expect(result.current.fullContent).toBe("ok");
  });

  // 14 — New streamMessage resets previous state
  it("resets state when a new stream is started", async () => {
    // First stream: error
    const errorPayload = ssePayload([
      { event: "status", data: { status: "started" } },
      {
        event: "error",
        data: {
          code: "FAIL",
          message: "first fail",
          retryable: false,
        },
      },
      { event: "done", data: { full_text: "" } },
    ]);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: stringStream(errorPayload),
    });

    const { result } = renderHook(() => useStreamingChat("conv-1"));

    await act(async () => {
      await result.current.streamMessage("fail");
    });

    expect(result.current.state).toBe("error");

    // Second stream: success
    const successPayload = ssePayload([
      { event: "status", data: { status: "started" } },
      { event: "data", data: { token: "fresh" } },
      { event: "done", data: { full_text: "fresh" } },
    ]);

    fetchMock.mockResolvedValueOnce({
      ok: true,
      body: stringStream(successPayload),
    });

    await act(async () => {
      await result.current.streamMessage("succeed");
    });

    expect(result.current.state).toBe("complete");
    expect(result.current.error).toBeNull();
    expect(result.current.fullContent).toBe("fresh");
  });
});
