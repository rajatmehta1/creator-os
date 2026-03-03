export interface AgentStatus {
  agentName: string;
  status: "idle" | "running" | "waiting_human" | "completed" | "error";
  currentNode?: string;
  progress: number;
  message?: string;
  timestamp: string;
}

export interface AgentOutput {
  agentName: string;
  runId: string;
  status: string;
  output: unknown;
  error?: string;
  durationSeconds: number;
  nodesExecuted: string[];
}

export interface OrchestratorStatus {
  runId: string;
  pipelineType: string;
  status: "running" | "waiting_gate" | "completed" | "error";
  currentAgent?: string;
  completedAgents: string[];
  pendingAgents: string[];
  agentOutputs: Record<string, unknown>;
  waitingGate?: string;
  startedAt: string;
  updatedAt: string;
}
