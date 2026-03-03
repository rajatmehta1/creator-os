"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/utils";
import type { Idea } from "@/types/content";

interface IdeaCardProps {
  idea: Idea;
  onApprove?: (ideaId: string) => void;
  onReject?: (ideaId: string) => void;
  onSendToScript?: (ideaId: string) => void;
}

function getViabilityColor(score: number): string {
  if (score >= 75) return "text-green-500";
  if (score >= 50) return "text-yellow-500";
  if (score >= 25) return "text-orange-500";
  return "text-red-500";
}

function getViabilityBg(score: number): string {
  if (score >= 75) return "bg-green-500";
  if (score >= 50) return "bg-yellow-500";
  if (score >= 25) return "bg-orange-500";
  return "bg-red-500";
}

const difficultyConfig: Record<string, string> = {
  easy: "bg-green-500/10 text-green-500 border-green-500/20",
  medium: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  hard: "bg-red-500/10 text-red-500 border-red-500/20",
};

function contentTypeLabel(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function IdeaCard({
  idea,
  onApprove,
  onReject,
  onSendToScript,
}: IdeaCardProps) {
  const [expanded, setExpanded] = useState(false);
  const viabilityScore = idea.score ?? 0;
  const difficulty = idea.difficulty?.toLowerCase() ?? "medium";

  return (
    <div className="rounded-lg border bg-card p-5 transition-shadow hover:shadow-md">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <h3 className="text-base font-semibold leading-tight">{idea.title}</h3>
          {idea.hook && (
            <p className="mt-1 text-sm text-muted-foreground italic line-clamp-2">
              &ldquo;{idea.hook}&rdquo;
            </p>
          )}
        </div>

        {/* Viability Score */}
        <div className="flex flex-col items-center gap-1">
          <span
            className={cn(
              "text-2xl font-bold tabular-nums",
              getViabilityColor(viabilityScore)
            )}
          >
            {viabilityScore}
          </span>
          <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
            Viability
          </span>
        </div>
      </div>

      {/* Score Bar */}
      <div className="mt-3">
        <div className="h-1.5 w-full rounded-full bg-secondary">
          <div
            className={cn(
              "h-1.5 rounded-full transition-all",
              getViabilityBg(viabilityScore)
            )}
            style={{ width: `${Math.min(viabilityScore, 100)}%` }}
          />
        </div>
      </div>

      {/* Badges */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center rounded-full border bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
          {contentTypeLabel(idea.contentType)}
        </span>
        {idea.difficulty && (
          <span
            className={cn(
              "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
              difficultyConfig[difficulty] ?? difficultyConfig.medium
            )}
          >
            {idea.difficulty}
          </span>
        )}
        {idea.secondaryTypes.map((type) => (
          <span
            key={type}
            className="inline-flex items-center rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground"
          >
            {contentTypeLabel(type)}
          </span>
        ))}
      </div>

      {/* Key Points (expandable) */}
      {idea.keyPoints.length > 0 && (
        <div className="mt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
          >
            <span
              className={cn(
                "inline-block transition-transform",
                expanded && "rotate-90"
              )}
            >
              &#9654;
            </span>
            Key Points ({idea.keyPoints.length})
          </button>
          {expanded && (
            <ul className="mt-2 space-y-1 pl-4">
              {idea.keyPoints.map((point, idx) => (
                <li
                  key={idx}
                  className="text-sm text-muted-foreground before:mr-2 before:content-['\2022']"
                >
                  {point}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Meta Info */}
      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        {idea.estimatedPerformance && (
          <span>
            Est. Performance:{" "}
            <span className="font-medium text-foreground">
              {idea.estimatedPerformance}
            </span>
          </span>
        )}
        {idea.differentiation && (
          <span>
            Differentiation:{" "}
            <span className="font-medium text-foreground">
              {idea.differentiation}
            </span>
          </span>
        )}
        {idea.targetAudienceSegment && (
          <span>
            Audience:{" "}
            <span className="font-medium text-foreground">
              {idea.targetAudienceSegment}
            </span>
          </span>
        )}
      </div>

      {/* Trend Connection */}
      {idea.trendConnection && (
        <div className="mt-3 rounded-md bg-primary/5 p-3">
          <p className="text-xs font-medium text-primary">Trend Connection</p>
          <p className="mt-0.5 text-sm text-foreground">{idea.trendConnection}</p>
        </div>
      )}

      {/* Actions */}
      <div className="mt-4 flex items-center justify-end gap-2">
        <button
          onClick={() => onReject?.(idea.id)}
          className="inline-flex items-center rounded-md border px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive hover:border-destructive/20"
        >
          Reject
        </button>
        <button
          onClick={() => onApprove?.(idea.id)}
          className="inline-flex items-center rounded-md border px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-accent"
        >
          Approve
        </button>
        <button
          onClick={() => onSendToScript?.(idea.id)}
          className="inline-flex items-center rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          Send to Script
        </button>
      </div>
    </div>
  );
}
