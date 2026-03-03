"use client";

import { cn } from "@/lib/utils";
import type { ContentType } from "@/types/content";

interface ContentTypeSelectorProps {
  selected: ContentType[];
  onChange: (selected: ContentType[]) => void;
  multiSelect?: boolean;
  className?: string;
}

interface ContentTypeOption {
  value: ContentType;
  label: string;
  icon: string;
  description: string;
}

const contentTypes: ContentTypeOption[] = [
  {
    value: "youtube_video",
    label: "YouTube Video",
    icon: "YT",
    description: "Long-form video content",
  },
  {
    value: "youtube_short",
    label: "YouTube Short",
    icon: "SH",
    description: "60-second vertical video",
  },
  {
    value: "blog_post",
    label: "Blog Post",
    icon: "BL",
    description: "Written article content",
  },
  {
    value: "twitter_thread",
    label: "Twitter Thread",
    icon: "TW",
    description: "Multi-tweet thread",
  },
  {
    value: "linkedin_post",
    label: "LinkedIn Post",
    icon: "LI",
    description: "Professional network post",
  },
  {
    value: "newsletter",
    label: "Newsletter",
    icon: "NL",
    description: "Email newsletter edition",
  },
  {
    value: "podcast_outline",
    label: "Podcast",
    icon: "PC",
    description: "Podcast episode outline",
  },
];

const iconColors: Record<ContentType, string> = {
  youtube_video: "bg-red-500/10 text-red-500",
  youtube_short: "bg-red-500/10 text-red-400",
  blog_post: "bg-blue-500/10 text-blue-500",
  twitter_thread: "bg-sky-500/10 text-sky-500",
  linkedin_post: "bg-indigo-500/10 text-indigo-500",
  newsletter: "bg-emerald-500/10 text-emerald-500",
  podcast_outline: "bg-violet-500/10 text-violet-500",
};

export default function ContentTypeSelector({
  selected,
  onChange,
  multiSelect = false,
  className,
}: ContentTypeSelectorProps) {
  function handleToggle(value: ContentType) {
    if (multiSelect) {
      if (selected.includes(value)) {
        onChange(selected.filter((v) => v !== value));
      } else {
        onChange([...selected, value]);
      }
    } else {
      // Single-select mode: only one at a time
      onChange(selected.includes(value) ? [] : [value]);
    }
  }

  return (
    <div className={cn("grid gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4", className)}>
      {contentTypes.map((type) => {
        const isSelected = selected.includes(type.value);
        return (
          <button
            key={type.value}
            onClick={() => handleToggle(type.value)}
            className={cn(
              "flex items-center gap-3 rounded-lg border p-3 text-left transition-all",
              isSelected
                ? "border-primary bg-primary/5 ring-1 ring-primary"
                : "border-border bg-card hover:bg-accent"
            )}
          >
            {/* Icon */}
            <div
              className={cn(
                "flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg text-xs font-bold",
                iconColors[type.value]
              )}
            >
              {type.icon}
            </div>

            {/* Label & Description */}
            <div className="flex-1 min-w-0">
              <p
                className={cn(
                  "text-sm font-medium",
                  isSelected ? "text-primary" : "text-foreground"
                )}
              >
                {type.label}
              </p>
              <p className="text-[11px] text-muted-foreground truncate">
                {type.description}
              </p>
            </div>

            {/* Selection indicator */}
            <div
              className={cn(
                "flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                isSelected
                  ? "border-primary bg-primary"
                  : "border-muted-foreground/30"
              )}
            >
              {isSelected && (
                <svg
                  className="h-3 w-3 text-primary-foreground"
                  viewBox="0 0 12 12"
                  fill="none"
                >
                  <path
                    d="M2.5 6L5 8.5L9.5 3.5"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
