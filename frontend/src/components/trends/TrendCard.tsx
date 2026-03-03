"use client";

import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/utils";
import type { Trend } from "@/types/trend";

interface TrendCardProps {
  trend: Trend;
  onGenerateIdeas?: (trendId: string) => void;
}

const velocityConfig = {
  emerging: { label: "Emerging", color: "bg-green-500/10 text-green-500 border-green-500/20" },
  peaking: { label: "Peaking", color: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20" },
  declining: { label: "Declining", color: "bg-red-500/10 text-red-500 border-red-500/20" },
  expired: { label: "Expired", color: "bg-gray-500/10 text-gray-500 border-gray-500/20" },
};

function getRelevanceColor(score: number): string {
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
}

function getRelevanceBg(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-yellow-500";
  if (score >= 40) return "bg-orange-500";
  return "bg-red-500";
}

export default function TrendCard({ trend, onGenerateIdeas }: TrendCardProps) {
  const velocity = velocityConfig[trend.velocity];
  const relevance = trend.relevanceScore ?? 0;

  return (
    <div className="rounded-lg border bg-card p-5 transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <h3 className="text-base font-semibold leading-tight">{trend.title}</h3>
          {trend.summary && (
            <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
              {trend.summary}
            </p>
          )}
        </div>

        {/* Relevance Score */}
        <div className="flex flex-col items-center gap-1">
          <span
            className={cn(
              "text-2xl font-bold tabular-nums",
              getRelevanceColor(relevance)
            )}
          >
            {relevance}
          </span>
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
            Relevance
          </span>
        </div>
      </div>

      {/* Velocity & Source Badges */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
            velocity.color
          )}
        >
          {velocity.label}
        </span>
        <span className="inline-flex items-center rounded-full border bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
          {trend.source}
        </span>
        {trend.category && (
          <span className="inline-flex items-center rounded-full border bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
            {trend.category}
          </span>
        )}
      </div>

      {/* Relevance Bar */}
      <div className="mt-3">
        <div className="h-1.5 w-full rounded-full bg-secondary">
          <div
            className={cn("h-1.5 rounded-full transition-all", getRelevanceBg(relevance))}
            style={{ width: `${Math.min(relevance, 100)}%` }}
          />
        </div>
      </div>

      {/* Niche Angle */}
      {trend.nicheAngle && (
        <div className="mt-3 rounded-md bg-primary/5 p-3">
          <p className="text-xs font-medium text-primary">Niche Angle</p>
          <p className="mt-0.5 text-sm text-foreground">{trend.nicheAngle}</p>
        </div>
      )}

      {/* Suggested Content Types */}
      {trend.suggestedContentTypes.length > 0 && (
        <div className="mt-3">
          <p className="text-xs font-medium text-muted-foreground">Suggested Content</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {trend.suggestedContentTypes.map((type) => (
              <span
                key={type}
                className="inline-flex items-center rounded-md bg-accent px-2 py-0.5 text-xs font-medium text-accent-foreground"
              >
                {type}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Meta Info Row */}
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {trend.competitionLevel && (
          <span>
            Competition:{" "}
            <span className="font-medium text-foreground">
              {trend.competitionLevel}
            </span>
          </span>
        )}
        {trend.timeSensitivity && (
          <span>
            Time Sensitivity:{" "}
            <span className="font-medium text-foreground">
              {trend.timeSensitivity}
            </span>
          </span>
        )}
        <span>Detected: {formatDate(trend.detectedAt)}</span>
      </div>

      {/* Related Topics */}
      {trend.relatedTopics.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {trend.relatedTopics.map((topic) => (
            <span
              key={topic}
              className="inline-flex items-center rounded-full bg-secondary/60 px-2 py-0.5 text-[11px] text-muted-foreground"
            >
              {topic}
            </span>
          ))}
        </div>
      )}

      {/* Action */}
      <div className="mt-4 flex justify-end">
        <button
          onClick={() => onGenerateIdeas?.(trend.id)}
          className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          Generate Ideas
        </button>
      </div>
    </div>
  );
}
