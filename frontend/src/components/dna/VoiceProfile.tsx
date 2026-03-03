"use client";

import { cn } from "@/lib/utils";
import type { CreatorDNA } from "@/types/user";

interface VoiceProfileProps {
  dna: CreatorDNA;
  className?: string;
}

function FormalitySlider({ level }: { level: number }) {
  const percentage = Math.round(level * 100);
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-muted-foreground">Casual</span>
      <div className="relative h-2 flex-1 rounded-full bg-secondary">
        <div
          className="absolute left-0 top-0 h-2 rounded-full bg-primary transition-all"
          style={{ width: `${percentage}%` }}
        />
        <div
          className="absolute top-1/2 h-4 w-4 -translate-y-1/2 rounded-full border-2 border-primary bg-card shadow-sm transition-all"
          style={{ left: `calc(${percentage}% - 8px)` }}
        />
      </div>
      <span className="text-xs text-muted-foreground">Formal</span>
    </div>
  );
}

function TagList({ items, emptyText }: { items: string[]; emptyText?: string }) {
  if (items.length === 0) {
    return (
      <p className="text-sm text-muted-foreground italic">
        {emptyText ?? "None detected yet"}
      </p>
    );
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item, idx) => (
        <span
          key={idx}
          className="inline-flex items-center rounded-md bg-accent px-2 py-0.5 text-xs font-medium text-accent-foreground"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function ProfileField({
  label,
  value,
}: {
  label: string;
  value?: string | null;
}) {
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-sm text-foreground">
        {value || <span className="italic text-muted-foreground">Not analyzed yet</span>}
      </p>
    </div>
  );
}

export default function VoiceProfile({ dna, className }: VoiceProfileProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-6", className)}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Voice Characteristics</h3>
          <p className="text-sm text-muted-foreground">
            Your unique content voice fingerprint
          </p>
        </div>
        {dna.confidenceScore !== undefined && (
          <div className="flex flex-col items-end">
            <span className="text-xs text-muted-foreground">Confidence</span>
            <span className="text-lg font-bold text-primary">
              {Math.round(dna.confidenceScore * 100)}%
            </span>
          </div>
        )}
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        {/* Signature Phrases */}
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Signature Phrases
          </p>
          <TagList items={dna.signaturePhrases} />
        </div>

        {/* Filler Words */}
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Filler Words
          </p>
          <TagList items={dna.fillerWords} />
        </div>

        {/* Humor Style */}
        <ProfileField label="Humor Style" value={dna.humorStyle} />

        {/* Audience Address Style */}
        <ProfileField label="Audience Address Style" value={dna.audienceAddressStyle} />

        {/* CTA Style */}
        <ProfileField label="Call-to-Action Style" value={dna.callToActionStyle} />

        {/* Hook Style */}
        <ProfileField label="Hook Style" value={dna.hookStyle} />

        {/* Pacing Pattern */}
        <ProfileField label="Pacing Pattern" value={dna.pacingPattern} />

        {/* Formality Level */}
        <div className="md:col-span-2">
          <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Formality Level
          </p>
          <FormalitySlider level={dna.formalityLevel ?? 0.5} />
        </div>
      </div>

      {/* Topic Clusters */}
      {dna.topicClusters.length > 0 && (
        <div className="mt-6 border-t pt-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Topic Clusters
          </p>
          <div className="flex flex-wrap gap-2">
            {dna.topicClusters.map((cluster) => (
              <span
                key={cluster.name}
                className="inline-flex items-center gap-1.5 rounded-full border bg-secondary/60 px-3 py-1 text-xs"
              >
                <span className="font-medium text-foreground">{cluster.name}</span>
                <span className="text-muted-foreground">
                  {Math.round(cluster.weight * 100)}%
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Footer meta */}
      <div className="mt-6 flex items-center justify-between border-t pt-4 text-xs text-muted-foreground">
        <span>Videos analyzed: {dna.videosAnalyzed}</span>
        {dna.lastUpdated && (
          <span>Last updated: {new Date(dna.lastUpdated).toLocaleDateString()}</span>
        )}
      </div>
    </div>
  );
}
