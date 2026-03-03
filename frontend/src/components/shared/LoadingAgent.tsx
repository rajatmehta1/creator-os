"use client";

import { cn } from "@/lib/utils";

interface LoadingAgentProps {
  agentName: string;
  currentNode?: string;
  message?: string;
  className?: string;
}

export default function LoadingAgent({
  agentName,
  currentNode,
  message,
  className,
}: LoadingAgentProps) {
  return (
    <div className={cn("flex items-start gap-4 rounded-lg border bg-card p-4", className)}>
      {/* Pulsing dots animation */}
      <div className="flex items-center gap-1 pt-1">
        <span className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:0ms]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:150ms]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-primary [animation-delay:300ms]" />
      </div>

      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-foreground">{agentName}</span>
          <span className="text-xs text-muted-foreground">is thinking...</span>
        </div>

        {currentNode && (
          <p className="mt-1 text-xs text-muted-foreground">
            Current step:{" "}
            <span className="font-medium text-primary">{currentNode}</span>
          </p>
        )}

        {message && (
          <p className="mt-1 text-sm text-muted-foreground">{message}</p>
        )}
      </div>
    </div>
  );
}
