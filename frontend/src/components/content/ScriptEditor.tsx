"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { ContentType } from "@/types/content";

interface ScriptSection {
  id: string;
  type: "hook" | "intro" | "body" | "climax" | "cta" | "end_screen";
  title: string;
  content: string;
  retentionHooks?: Array<{ position: number; text: string }>;
}

interface ScriptEditorProps {
  sections: ScriptSection[];
  onSectionChange?: (sectionId: string, content: string) => void;
  activePlatform?: ContentType;
  onPlatformChange?: (platform: ContentType) => void;
  readOnly?: boolean;
  className?: string;
}

const platformTabs: Array<{ value: ContentType; label: string }> = [
  { value: "youtube_video", label: "YouTube" },
  { value: "blog_post", label: "Blog" },
  { value: "twitter_thread", label: "Twitter" },
  { value: "linkedin_post", label: "LinkedIn" },
  { value: "newsletter", label: "Newsletter" },
  { value: "youtube_short", label: "Shorts" },
];

const sectionConfig: Record<
  ScriptSection["type"],
  { label: string; color: string; bgColor: string }
> = {
  hook: { label: "Hook", color: "text-red-500", bgColor: "bg-red-500/10 border-red-500/20" },
  intro: { label: "Intro", color: "text-blue-500", bgColor: "bg-blue-500/10 border-blue-500/20" },
  body: { label: "Body Segment", color: "text-purple-500", bgColor: "bg-purple-500/10 border-purple-500/20" },
  climax: { label: "Climax", color: "text-orange-500", bgColor: "bg-orange-500/10 border-orange-500/20" },
  cta: { label: "Call to Action", color: "text-green-500", bgColor: "bg-green-500/10 border-green-500/20" },
  end_screen: { label: "End Screen", color: "text-gray-500", bgColor: "bg-gray-500/10 border-gray-500/20" },
};

function RetentionAnnotation({ text }: { text: string }) {
  return (
    <span className="ml-1 inline-flex items-center rounded bg-yellow-500/10 px-1.5 py-0.5 text-[10px] font-medium text-yellow-600 border border-yellow-500/20">
      Retention: {text}
    </span>
  );
}

function CollapsibleSection({
  section,
  onChange,
  readOnly,
}: {
  section: ScriptSection;
  onChange?: (content: string) => void;
  readOnly?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(true);
  const config = sectionConfig[section.type];

  return (
    <div className={cn("rounded-lg border", config.bgColor)}>
      {/* Section Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "inline-block transition-transform text-xs",
              isOpen && "rotate-90"
            )}
          >
            &#9654;
          </span>
          <span className={cn("text-sm font-semibold", config.color)}>
            {config.label}
          </span>
          {section.title && section.title !== config.label && (
            <span className="text-xs text-muted-foreground">
              - {section.title}
            </span>
          )}
        </div>
        <span className="text-xs text-muted-foreground">
          {section.content.split(/\s+/).filter(Boolean).length} words
        </span>
      </button>

      {/* Section Content */}
      {isOpen && (
        <div className="border-t px-4 py-3">
          {readOnly ? (
            <div className="text-sm leading-relaxed text-foreground whitespace-pre-wrap">
              {section.content}
              {/* Inline retention hook annotations */}
              {section.retentionHooks?.map((hook, idx) => (
                <div key={idx} className="mt-2">
                  <RetentionAnnotation text={hook.text} />
                </div>
              ))}
            </div>
          ) : (
            <>
              <textarea
                value={section.content}
                onChange={(e) => onChange?.(e.target.value)}
                className="w-full min-h-[120px] rounded-md border bg-background p-3 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-y"
                placeholder={`Write your ${config.label.toLowerCase()} here...`}
              />
              {/* Retention hook annotations below editor */}
              {section.retentionHooks && section.retentionHooks.length > 0 && (
                <div className="mt-2 space-y-1">
                  {section.retentionHooks.map((hook, idx) => (
                    <div key={idx} className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground">
                        @pos {hook.position}:
                      </span>
                      <RetentionAnnotation text={hook.text} />
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function ScriptEditor({
  sections,
  onSectionChange,
  activePlatform = "youtube_video",
  onPlatformChange,
  readOnly = false,
  className,
}: ScriptEditorProps) {
  return (
    <div className={cn("rounded-lg border bg-card", className)}>
      {/* Platform Tabs */}
      <div className="flex items-center gap-1 border-b px-4 py-2 overflow-x-auto">
        {platformTabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => onPlatformChange?.(tab.value)}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-medium transition-colors whitespace-nowrap",
              activePlatform === tab.value
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Script Sections */}
      <div className="space-y-3 p-4">
        {sections.length === 0 ? (
          <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
            No script sections yet. Generate a script to get started.
          </div>
        ) : (
          sections.map((section) => (
            <CollapsibleSection
              key={section.id}
              section={section}
              onChange={
                onSectionChange
                  ? (content) => onSectionChange(section.id, content)
                  : undefined
              }
              readOnly={readOnly}
            />
          ))
        )}
      </div>

      {/* Footer with word count */}
      {sections.length > 0 && (
        <div className="border-t px-4 py-2 text-xs text-muted-foreground">
          Total:{" "}
          {sections
            .reduce(
              (acc, s) => acc + s.content.split(/\s+/).filter(Boolean).length,
              0
            )}{" "}
          words | {sections.length} sections
        </div>
      )}
    </div>
  );
}
