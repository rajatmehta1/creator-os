"use client";

import { cn } from "@/lib/utils";
import { formatDate } from "@/lib/utils";
import type { Content, ContentStatus } from "@/types/content";

interface ContentPipelineProps {
  items: Content[];
  onItemClick?: (contentId: string) => void;
  className?: string;
}

interface PipelineColumn {
  status: ContentStatus;
  label: string;
  color: string;
  headerBg: string;
}

const columns: PipelineColumn[] = [
  {
    status: "idea",
    label: "Idea",
    color: "text-blue-500",
    headerBg: "bg-blue-500/10 border-blue-500/20",
  },
  {
    status: "draft",
    label: "Draft",
    color: "text-yellow-500",
    headerBg: "bg-yellow-500/10 border-yellow-500/20",
  },
  {
    status: "review",
    label: "Review",
    color: "text-purple-500",
    headerBg: "bg-purple-500/10 border-purple-500/20",
  },
  {
    status: "optimized",
    label: "Optimized",
    color: "text-orange-500",
    headerBg: "bg-orange-500/10 border-orange-500/20",
  },
  {
    status: "published",
    label: "Published",
    color: "text-green-500",
    headerBg: "bg-green-500/10 border-green-500/20",
  },
];

function contentTypeLabel(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

const contentTypeBadgeColor: Record<string, string> = {
  youtube_video: "bg-red-500/10 text-red-500 border-red-500/20",
  youtube_short: "bg-red-500/10 text-red-400 border-red-400/20",
  blog_post: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  twitter_thread: "bg-sky-500/10 text-sky-500 border-sky-500/20",
  linkedin_post: "bg-indigo-500/10 text-indigo-500 border-indigo-500/20",
  newsletter: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
  podcast_outline: "bg-violet-500/10 text-violet-500 border-violet-500/20",
};

function PipelineCard({
  item,
  onClick,
}: {
  item: Content;
  onClick?: () => void;
}) {
  const badgeColor =
    contentTypeBadgeColor[item.contentType] ??
    "bg-secondary text-secondary-foreground";

  return (
    <button
      onClick={onClick}
      className="w-full rounded-lg border bg-card p-3 text-left transition-shadow hover:shadow-md"
    >
      <p className="text-sm font-medium leading-tight text-foreground line-clamp-2">
        {item.title}
      </p>

      <div className="mt-2 flex items-center gap-2">
        <span
          className={cn(
            "inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium",
            badgeColor
          )}
        >
          {contentTypeLabel(item.contentType)}
        </span>
      </div>

      <p className="mt-2 text-[10px] text-muted-foreground">
        Updated {formatDate(item.updatedAt)}
      </p>
    </button>
  );
}

export default function ContentPipeline({
  items,
  onItemClick,
  className,
}: ContentPipelineProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-4", className)}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Content Pipeline</h2>
        <span className="text-xs text-muted-foreground">
          {items.length} total items
        </span>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-2">
        {columns.map((col) => {
          const columnItems = items.filter((item) => item.status === col.status);
          return (
            <div key={col.status} className="flex w-56 min-w-[14rem] flex-shrink-0 flex-col">
              {/* Column Header */}
              <div
                className={cn(
                  "flex items-center justify-between rounded-t-lg border px-3 py-2",
                  col.headerBg
                )}
              >
                <span className={cn("text-xs font-semibold", col.color)}>
                  {col.label}
                </span>
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-secondary text-[10px] font-medium text-secondary-foreground">
                  {columnItems.length}
                </span>
              </div>

              {/* Column Body */}
              <div className="flex flex-1 flex-col gap-2 rounded-b-lg border border-t-0 bg-secondary/20 p-2 min-h-[200px]">
                {columnItems.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                    No items
                  </div>
                ) : (
                  columnItems.map((item) => (
                    <PipelineCard
                      key={item.id}
                      item={item}
                      onClick={() => onItemClick?.(item.id)}
                    />
                  ))
                )}

                {/* Drop zone stub for visual affordance */}
                <div className="mt-auto rounded-lg border-2 border-dashed border-transparent p-2 text-center text-[10px] text-muted-foreground opacity-0 transition-opacity hover:opacity-50">
                  Drop here
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
