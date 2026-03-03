"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface ConsoleEntry {
  type: "node_start" | "output" | "error" | "info";
  text: string;
  timestamp?: string;
}

interface AgentConsoleProps {
  entries: ConsoleEntry[];
  title?: string;
  isStreaming?: boolean;
  className?: string;
}

function formatTime(timestamp?: string): string {
  if (!timestamp) return "";
  const d = new Date(timestamp);
  return d.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export default function AgentConsole({
  entries,
  title = "Agent Console",
  isStreaming = false,
  className,
}: AgentConsoleProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries]);

  return (
    <div className={cn("flex flex-col rounded-lg border overflow-hidden", className)}>
      {/* Header */}
      <div className="flex items-center justify-between bg-gray-900 px-4 py-2.5">
        <div className="flex items-center gap-2">
          {/* Terminal dots */}
          <div className="flex gap-1.5">
            <div className="h-2.5 w-2.5 rounded-full bg-red-500" />
            <div className="h-2.5 w-2.5 rounded-full bg-yellow-500" />
            <div className="h-2.5 w-2.5 rounded-full bg-green-500" />
          </div>
          <span className="ml-2 text-xs font-medium text-gray-400">{title}</span>
        </div>
        {isStreaming && (
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 animate-pulse rounded-full bg-green-500" />
            <span className="text-[10px] text-green-400">LIVE</span>
          </div>
        )}
      </div>

      {/* Console Body */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto bg-gray-950 p-4 font-mono text-xs leading-relaxed min-h-[200px] max-h-[500px]"
      >
        {entries.length === 0 ? (
          <p className="text-gray-600">Waiting for agent output...</p>
        ) : (
          entries.map((entry, idx) => (
            <div key={idx} className="mb-1">
              {entry.type === "node_start" ? (
                <div className="my-2 flex items-center gap-2">
                  <span className="text-blue-400 font-bold">
                    --- {entry.text} ---
                  </span>
                  {entry.timestamp && (
                    <span className="text-gray-600">
                      [{formatTime(entry.timestamp)}]
                    </span>
                  )}
                </div>
              ) : entry.type === "error" ? (
                <div className="flex gap-2">
                  {entry.timestamp && (
                    <span className="text-gray-600 flex-shrink-0">
                      [{formatTime(entry.timestamp)}]
                    </span>
                  )}
                  <span className="text-red-400">{entry.text}</span>
                </div>
              ) : entry.type === "info" ? (
                <div className="flex gap-2">
                  {entry.timestamp && (
                    <span className="text-gray-600 flex-shrink-0">
                      [{formatTime(entry.timestamp)}]
                    </span>
                  )}
                  <span className="text-yellow-400">{entry.text}</span>
                </div>
              ) : (
                <div className="flex gap-2">
                  {entry.timestamp && (
                    <span className="text-gray-600 flex-shrink-0">
                      [{formatTime(entry.timestamp)}]
                    </span>
                  )}
                  <span className="text-gray-300 whitespace-pre-wrap">
                    {entry.text}
                  </span>
                </div>
              )}
            </div>
          ))
        )}

        {/* Blinking cursor when streaming */}
        {isStreaming && (
          <span className="inline-block h-3.5 w-1.5 animate-pulse bg-green-500" />
        )}
      </div>
    </div>
  );
}
