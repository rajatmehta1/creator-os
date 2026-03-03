export interface Trend {
  id: string;
  title: string;
  summary?: string;
  source: string;
  category?: string;
  relevanceScore?: number;
  velocity: "emerging" | "peaking" | "declining" | "expired";
  competitionLevel?: string;
  detectedAt: string;
  nicheAngle?: string;
  suggestedContentTypes: string[];
  timeSensitivity?: string;
  relatedTopics: string[];
}

export interface TrendCluster {
  clusterName: string;
  trends: Trend[];
  combinedScore: number;
}
