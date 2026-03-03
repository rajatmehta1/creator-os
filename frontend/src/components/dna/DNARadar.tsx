"use client";

import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { cn } from "@/lib/utils";
import type { CreatorDNA } from "@/types/user";

interface DNARadarProps {
  dna: CreatorDNA;
  className?: string;
}

/** Map pacing pattern strings to a numeric 0-100 scale */
function pacingToNumber(pacing?: string): number {
  const map: Record<string, number> = {
    slow: 20,
    "slow-medium": 35,
    medium: 50,
    "medium-fast": 65,
    fast: 80,
    rapid: 95,
  };
  if (!pacing) return 50;
  return map[pacing.toLowerCase()] ?? 50;
}

/** Map hook style strings to a numeric 0-100 scale */
function hookStyleToNumber(style?: string): number {
  const map: Record<string, number> = {
    question: 60,
    story: 75,
    statistic: 55,
    bold_claim: 85,
    contrarian: 90,
    curiosity: 70,
    direct: 40,
    emotional: 80,
  };
  if (!style) return 50;
  return map[style.toLowerCase()] ?? 50;
}

function buildRadarData(dna: CreatorDNA) {
  return [
    {
      dimension: "Vocabulary",
      value: Math.round((dna.vocabularyComplexity ?? 0.5) * 100),
      fullMark: 100,
    },
    {
      dimension: "Humor",
      value: Math.round((dna.humorFrequency ?? 0.5) * 100),
      fullMark: 100,
    },
    {
      dimension: "Formality",
      value: Math.round((dna.formalityLevel ?? 0.5) * 100),
      fullMark: 100,
    },
    {
      dimension: "Vulnerability",
      value: Math.round((dna.vulnerabilityLevel ?? 0.5) * 100),
      fullMark: 100,
    },
    {
      dimension: "Storytelling",
      value: Math.round((dna.storytellingFrequency ?? 0.5) * 100),
      fullMark: 100,
    },
    {
      dimension: "Technical Depth",
      value: Math.round(
        (Object.values(dna.expertiseDepth).length > 0
          ? Object.values(dna.expertiseDepth).reduce((a, b) => a + b, 0) /
            Object.values(dna.expertiseDepth).length
          : 0.5) * 100
      ),
      fullMark: 100,
    },
    {
      dimension: "Pacing",
      value: pacingToNumber(dna.pacingPattern),
      fullMark: 100,
    },
    {
      dimension: "Hook Style",
      value: hookStyleToNumber(dna.hookStyle),
      fullMark: 100,
    },
  ];
}

export default function DNARadar({ dna, className }: DNARadarProps) {
  const data = buildRadarData(dna);

  return (
    <div className={cn("rounded-lg border bg-card p-6", className)}>
      <h3 className="text-sm font-semibold">Creator DNA Profile</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        8 dimensions of your unique content voice
      </p>

      <div className="mt-4 h-80">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
            <PolarGrid className="stroke-border" />
            <PolarAngleAxis
              dataKey="dimension"
              tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fontSize: 10 }}
              className="text-muted-foreground"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                fontSize: "12px",
              }}
            />
            <Radar
              name="DNA"
              dataKey="value"
              stroke="hsl(var(--primary))"
              fill="hsl(var(--primary))"
              fillOpacity={0.2}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Confidence Score */}
      {dna.confidenceScore !== undefined && (
        <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
          <span>
            DNA Confidence:{" "}
            <span className="font-medium text-foreground">
              {Math.round(dna.confidenceScore * 100)}%
            </span>
          </span>
          <span>Videos Analyzed: {dna.videosAnalyzed}</span>
        </div>
      )}
    </div>
  );
}
