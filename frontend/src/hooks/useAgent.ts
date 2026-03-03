"use client";

import { useCallback, useRef, useState } from "react";

interface AgentProgress {
  node: string;
  status: string;
  message?: string;
  progress?: number;
}

interface UseAgentOptions {
  baseUrl?: string;
}

interface UseAgentReturn {
  invoke: (agentName: string, input: Record<string, unknown>) => void;
  cancel: () => void;
  isLoading: boolean;
  output: unknown | null;
  error: string | null;
  progress: AgentProgress | null;
  streamText: string;
}

export function useAgent(options?: UseAgentOptions): UseAgentReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [output, setOutput] = useState<unknown | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<AgentProgress | null>(null);
  const [streamText, setStreamText] = useState("");
  const eventSourceRef = useRef<EventSource | null>(null);

  const baseUrl =
    options?.baseUrl ??
    (typeof window !== "undefined"
      ? process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"
      : "http://localhost:8000");

  const cancel = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsLoading(false);
  }, []);

  const invoke = useCallback(
    (agentName: string, input: Record<string, unknown>) => {
      // Reset state
      setIsLoading(true);
      setOutput(null);
      setError(null);
      setProgress(null);
      setStreamText("");

      // Close any existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Build URL with query params for the SSE endpoint
      const params = new URLSearchParams({
        agent: agentName,
        input: JSON.stringify(input),
      });
      const url = `${baseUrl}/api/v1/agents/stream?${params.toString()}`;

      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.addEventListener("progress", (event) => {
        try {
          const data = JSON.parse(event.data) as AgentProgress;
          setProgress(data);
        } catch {
          // Ignore parse errors
        }
      });

      es.addEventListener("stream", (event) => {
        setStreamText((prev) => prev + event.data);
      });

      es.addEventListener("output", (event) => {
        try {
          const data = JSON.parse(event.data);
          setOutput(data);
        } catch {
          setOutput(event.data);
        }
      });

      es.addEventListener("error", (event) => {
        if (event instanceof MessageEvent && event.data) {
          setError(event.data);
        } else {
          setError("Connection to agent failed");
        }
        setIsLoading(false);
        es.close();
        eventSourceRef.current = null;
      });

      es.addEventListener("done", () => {
        setIsLoading(false);
        es.close();
        eventSourceRef.current = null;
      });

      // Native onerror handler for connection failures
      es.onerror = () => {
        // EventSource will auto-retry on error. If we get an error
        // after we already received a "done" event, readyState will be CLOSED.
        if (es.readyState === EventSource.CLOSED) {
          setIsLoading(false);
          eventSourceRef.current = null;
        }
      };
    },
    [baseUrl]
  );

  return { invoke, cancel, isLoading, output, error, progress, streamText };
}
