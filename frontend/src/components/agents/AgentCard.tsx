"use client";

import { cn } from "@/lib/utils";
import type { AgentStatus } from "@/types/agent";

interface AgentCardProps {
  agent: AgentStatus;
  className?: string;
}

const statusConfig: Record<
  AgentStatus["status"],
  { label: string; color: string; dotColor: string }
> = {
  idle: {
    label: "Idle",
    color: "bg-gray-500/10 text-gray-500 border-gray-500/20",
    dotColor: "bg-gray-400",
  },
  running: {
    label: "Running",
    color: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    dotColor: "bg-blue-500",
  },
  waiting_human: {
    label: "Waiting",
    color: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    dotColor: "bg-yellow-500",
  },
  completed: {
    label: "Completed",
    color: "bg-green-500/10 text-green-500 border-green-500/20",
    dotColor: "bg-green-500",
  },
  error: {
    label: "Error",
    color: "bg-red-500/10 text-red-500 border-red-500/20",
    dotColor: "bg-red-500",
  },
};

function formatDuration(timestamp: string): string {
  const elapsed = Date.now() - new Date(timestamp).getTime();
  const seconds = Math.floor(elapsed / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  return `${minutes}m ${remaining}s`;
}

export default function AgentCard({ agent, className }: AgentCardProps) {
  const config = statusConfig[agent.status];

  return (
    <div className={cn("rounded-lg border bg-card p-4 transition-shadow hover:shadow-sm", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">{agent.agentName}</h3>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-medium",
            config.color
          )}
        >
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              config.dotColor,
              agent.status === "running" && "animate-pulse"
            )}
          />
          {config.label}
        </span>
      </div>

      {/* Current Node */}
      {agent.currentNode && (
        <p className="mt-2 text-xs text-muted-foreground">
          Step:{" "}
          <span className="font-medium text-foreground">{agent.currentNode}</span>
        </p>
      )}

      {/* Progress Bar */}
      <div className="mt-3">
        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
          <span>Progress</span>
          <span>{Math.round(agent.progress * 100)}%</span>
        </div>
        <div className="mt-1 h-1.5 w-full rounded-full bg-secondary">
          <div
            className={cn(
              "h-1.5 rounded-full transition-all duration-500",
              agent.status === "error"
                ? "bg-red-500"
                : agent.status === "completed"
                ? "bg-green-500"
                : "bg-primary"
            )}
            style={{ width: `${Math.min(agent.progress * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* Duration */}
      <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
        <span>Duration: {formatDuration(agent.timestamp)}</span>
        {agent.message && (
          <span className="truncate ml-2 max-w-[60%] text-right" title={agent.message}>
            {agent.message}
          </span>
        )}
      </div>
    </div>
  );
}
