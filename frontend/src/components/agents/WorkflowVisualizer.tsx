"use client";

import { cn } from "@/lib/utils";

interface WorkflowStep {
  agent: string;
  label: string;
  status: "pending" | "running" | "completed" | "error" | "waiting";
}

interface WorkflowVisualizerProps {
  steps: WorkflowStep[];
  currentAgent?: string;
}

const STATUS_STYLES = {
  pending: "border-gray-300 bg-gray-50 text-gray-500 dark:border-gray-700 dark:bg-gray-800",
  running: "border-primary bg-primary/10 text-primary animate-pulse",
  completed: "border-green-500 bg-green-50 text-green-700 dark:bg-green-950/20 dark:text-green-400",
  error: "border-red-500 bg-red-50 text-red-700 dark:bg-red-950/20 dark:text-red-400",
  waiting: "border-yellow-500 bg-yellow-50 text-yellow-700 dark:bg-yellow-950/20 dark:text-yellow-400",
};

const STATUS_DOTS = {
  pending: "bg-gray-400",
  running: "bg-primary animate-pulse",
  completed: "bg-green-500",
  error: "bg-red-500",
  waiting: "bg-yellow-500 animate-pulse",
};

export default function WorkflowVisualizer({
  steps,
  currentAgent,
}: WorkflowVisualizerProps) {
  return (
    <div className="rounded-lg border bg-card p-6">
      <h3 className="mb-4 text-sm font-semibold">Pipeline Progress</h3>

      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={step.agent} className="flex items-center">
            {/* Step node */}
            <div
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all",
                STATUS_STYLES[step.status]
              )}
            >
              <div className={cn("h-3 w-3 rounded-full", STATUS_DOTS[step.status])} />
              <span className="text-xs font-medium">{step.label}</span>
              <span className="text-[10px] capitalize">{step.status}</span>
            </div>

            {/* Connector line */}
            {index < steps.length - 1 && (
              <div
                className={cn(
                  "mx-2 h-0.5 w-12",
                  step.status === "completed" ? "bg-green-500" : "bg-gray-300 dark:bg-gray-700"
                )}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
