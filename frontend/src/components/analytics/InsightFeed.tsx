"use client";

import { cn } from "@/lib/utils";

interface Insight {
  insight: string;
  category: string;
  priority: "high" | "medium" | "low";
  action: string;
  expectedImpact: string;
}

interface InsightFeedProps {
  insights: Insight[];
}

const PRIORITY_STYLES = {
  high: "border-l-red-500 bg-red-50 dark:bg-red-950/20",
  medium: "border-l-yellow-500 bg-yellow-50 dark:bg-yellow-950/20",
  low: "border-l-blue-500 bg-blue-50 dark:bg-blue-950/20",
};

const CATEGORY_BADGES: Record<string, string> = {
  content: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  growth: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  engagement: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  seo: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  monetization: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
};

export default function InsightFeed({ insights }: InsightFeedProps) {
  if (insights.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center">
        <p className="text-sm text-muted-foreground">No insights yet. Sync your analytics to generate AI insights.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {insights.map((insight, i) => (
        <div
          key={i}
          className={cn(
            "rounded-lg border-l-4 p-4",
            PRIORITY_STYLES[insight.priority]
          )}
        >
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "rounded-full px-2 py-0.5 text-xs font-medium",
                CATEGORY_BADGES[insight.category] || "bg-gray-100 text-gray-800"
              )}
            >
              {insight.category}
            </span>
            <span className="text-xs font-medium uppercase text-muted-foreground">
              {insight.priority} priority
            </span>
          </div>
          <p className="mt-2 text-sm font-medium">{insight.insight}</p>
          <div className="mt-2 rounded bg-background/50 p-2">
            <p className="text-xs font-medium text-muted-foreground">Action:</p>
            <p className="text-sm">{insight.action}</p>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Expected impact: {insight.expectedImpact}
          </p>
        </div>
      ))}
    </div>
  );
}
