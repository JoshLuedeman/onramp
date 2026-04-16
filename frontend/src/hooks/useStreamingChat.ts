/**
 * useStreamingChat — Custom hook for chat streaming with error recovery.
 *
 * Handles typed SSE events (data, error, done, status), exponential backoff
 * retry on transient failures (max 3 retries), and preserves partial content
 * when the stream drops mid-response.
 *
 * State machine: idle → streaming → complete | error → (retry) → streaming
 */

import { useState, useCallback, useRef } from "react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Streaming state machine states. */
export type StreamingState = "idle" | "streaming" | "complete" | "error";

/** Typed SSE event from the backend. */
export interface StreamEvent {
  type: "data" | "error" | "done" | "status";
  payload: Record<string, unknown>;
}

/** Error detail from a stream error event. */
export interface StreamError {
  code: string;
  message: string;
  retryable: boolean;
}

/** Return value of the `useStreamingChat` hook. */
export interface UseStreamingChatReturn {
  /** Start streaming a message. */
  streamMessage: (content: string) => Promise<void>;
  /** Cancel an in-progress stream and reset to idle. */
  cancel: () => void;
  /** Current streaming state. */
  state: StreamingState;
  /** Whether a stream is currently in progress. */
  isStreaming: boolean;
  /** Last error that occurred during streaming. */
  error: StreamError | null;
  /** Partial content accumulated so far (preserved on error). */
  partialContent: string;
  /** Full response text once streaming completes. */
  fullContent: string;
  /** Current retry count. */
  retryCount: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_RETRIES = 3;
const INITIAL_BACKOFF_MS = 1_000;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useStreamingChat(
  conversationId: string,
): UseStreamingChatReturn {
  const [state, setState] = useState<StreamingState>("idle");
  const [error, setError] = useState<StreamError | null>(null);
  const [partialContent, setPartialContent] = useState("");
  const [fullContent, setFullContent] = useState("");
  const [retryCount, setRetryCount] = useState(0);

  const abortRef = useRef<AbortController | null>(null);
  const retryCountRef = useRef(0);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState("idle");
  }, []);

  const streamMessage = useCallback(
    async (content: string) => {
      // Reset state for a new stream
      setError(null);
      setPartialContent("");
      setFullContent("");
      setState("streaming");
      retryCountRef.current = 0;
      setRetryCount(0);

      const attemptStream = async (attempt: number): Promise<void> => {
        const controller = new AbortController();
        abortRef.current = controller;

        try {
          const response = await fetch(
            `/api/chat/${conversationId}/stream`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ content }),
              signal: controller.signal,
            },
          );

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const reader = response.body?.getReader();
          if (!reader) {
            throw new Error("No response body reader available");
          }

          const decoder = new TextDecoder();
          let buffer = "";
          let accumulated = "";

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Parse SSE events from buffer
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? ""; // Keep incomplete line

            let eventType = "";
            for (const line of lines) {
              if (line.startsWith("event: ")) {
                eventType = line.slice(7).trim();
              } else if (line.startsWith("data: ") && eventType) {
                const dataStr = line.slice(6);
                try {
                  const payload = JSON.parse(dataStr);
                  if (eventType === "data" && payload.token) {
                    accumulated += payload.token;
                    setPartialContent(accumulated);
                  } else if (eventType === "error") {
                    const streamErr: StreamError = {
                      code: payload.code ?? "UNKNOWN",
                      message: payload.message ?? "Unknown error",
                      retryable: payload.retryable ?? false,
                    };

                    // Retry transient failures
                    if (streamErr.retryable && attempt < MAX_RETRIES) {
                      const backoff =
                        INITIAL_BACKOFF_MS * Math.pow(2, attempt);
                      retryCountRef.current = attempt + 1;
                      setRetryCount(attempt + 1);
                      await new Promise((r) => setTimeout(r, backoff));
                      return attemptStream(attempt + 1);
                    }

                    setError(streamErr);
                    setState("error");
                    return;
                  } else if (eventType === "done") {
                    const text = payload.full_text ?? accumulated;
                    setFullContent(text);
                    setPartialContent(text);
                    setState("complete");
                    return;
                  }
                  // status events — no-op for now
                } catch {
                  // Ignore malformed JSON
                }
                eventType = "";
              } else if (line === "") {
                eventType = "";
              }
            }
          }

          // Stream ended without a done event — treat accumulated as final
          if (accumulated) {
            setFullContent(accumulated);
            setState("complete");
          } else {
            setState("idle");
          }
        } catch (err: unknown) {
          if (err instanceof DOMException && err.name === "AbortError") {
            // Cancelled — don't set error
            return;
          }

          const message =
            err instanceof Error ? err.message : "Stream connection failed";
          const isTransient =
            message.includes("timeout") ||
            message.includes("network") ||
            message.includes("fetch");

          if (isTransient && attempt < MAX_RETRIES) {
            const backoff = INITIAL_BACKOFF_MS * Math.pow(2, attempt);
            retryCountRef.current = attempt + 1;
            setRetryCount(attempt + 1);
            await new Promise((r) => setTimeout(r, backoff));
            return attemptStream(attempt + 1);
          }

          setError({
            code: "CONNECTION_ERROR",
            message,
            retryable: false,
          });
          setState("error");
        }
      };

      await attemptStream(0);
    },
    [conversationId],
  );

  return {
    streamMessage,
    cancel,
    state,
    isStreaming: state === "streaming",
    error,
    partialContent,
    fullContent,
    retryCount,
  };
}
