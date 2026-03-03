"use client";

import { formatNumber } from "@/lib/utils";

interface MediaKitData {
  channelStats: {
    title?: string;
    subscriberCount?: number;
    totalViews?: number;
    videoCount?: number;
    avgViewsPerVideo?: number;
  };
  demographics: Record<string, unknown>;
  growthMetrics: {
    growth30d?: number;
    growth60d?: number;
    growth90d?: number;
  };
  topVideos: Array<{ title: string; views: number }>;
  brandSafety: { score: number; analysis: string };
  rateCard: {
    suggestedCpm?: number;
    suggestedFlatRate?: number;
    formats?: Record<string, number>;
  };
  collaborationFormats: Array<{ name: string; description: string }>;
}

interface MediaKitPreviewProps {
  data: MediaKitData;
}

export default function MediaKitPreview({ data }: MediaKitPreviewProps) {
  const { channelStats, growthMetrics, topVideos, brandSafety, rateCard, collaborationFormats } = data;

  return (
    <div className="mx-auto max-w-4xl space-y-8 rounded-xl border bg-card p-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold">{channelStats.title || "Creator"}</h1>
        <p className="mt-2 text-muted-foreground">Media Kit</p>
      </div>

      {/* Key Stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatBox label="Subscribers" value={formatNumber(channelStats.subscriberCount || 0)} />
        <StatBox label="Total Views" value={formatNumber(channelStats.totalViews || 0)} />
        <StatBox label="Videos" value={String(channelStats.videoCount || 0)} />
        <StatBox label="Avg Views" value={formatNumber(channelStats.avgViewsPerVideo || 0)} />
      </div>

      {/* Growth */}
      <div>
        <h2 className="text-lg font-semibold">Growth Trajectory</h2>
        <div className="mt-3 grid grid-cols-3 gap-4">
          <GrowthMetric period="30 days" growth={growthMetrics.growth30d || 0} />
          <GrowthMetric period="60 days" growth={growthMetrics.growth60d || 0} />
          <GrowthMetric period="90 days" growth={growthMetrics.growth90d || 0} />
        </div>
      </div>

      {/* Top Videos */}
      {topVideos.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold">Top Performing Content</h2>
          <div className="mt-3 space-y-2">
            {topVideos.slice(0, 5).map((video, i) => (
              <div key={i} className="flex items-center justify-between rounded-lg border p-3">
                <span className="text-sm font-medium">{video.title}</span>
                <span className="text-sm text-muted-foreground">{formatNumber(video.views)} views</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Brand Safety */}
      <div>
        <h2 className="text-lg font-semibold">Brand Safety</h2>
        <div className="mt-3 flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <span className="text-xl font-bold text-primary">{brandSafety.score}</span>
          </div>
          <p className="text-sm text-muted-foreground">{brandSafety.analysis}</p>
        </div>
      </div>

      {/* Rate Card */}
      {rateCard.suggestedFlatRate && (
        <div>
          <h2 className="text-lg font-semibold">Collaboration Rates</h2>
          <div className="mt-3 grid grid-cols-2 gap-3">
            {rateCard.formats &&
              Object.entries(rateCard.formats).map(([format, price]) => (
                <div key={format} className="rounded-lg border p-3">
                  <p className="text-sm font-medium capitalize">{format.replace(/_/g, " ")}</p>
                  <p className="text-lg font-bold text-primary">${price}</p>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Collaboration Formats */}
      {collaborationFormats.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold">Collaboration Formats</h2>
          <div className="mt-3 grid grid-cols-2 gap-3">
            {collaborationFormats.map((format, i) => (
              <div key={i} className="rounded-lg border p-3">
                <p className="text-sm font-semibold">{format.name}</p>
                <p className="text-xs text-muted-foreground">{format.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border p-4 text-center">
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function GrowthMetric({ period, growth }: { period: string; growth: number }) {
  return (
    <div className="rounded-lg border p-4">
      <p className="text-sm text-muted-foreground">{period}</p>
      <p className={`text-lg font-bold ${growth >= 0 ? "text-green-600" : "text-red-600"}`}>
        {growth >= 0 ? "+" : ""}{growth.toFixed(1)}%
      </p>
    </div>
  );
}
