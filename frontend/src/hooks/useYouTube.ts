"use client";

import { useCallback, useState } from "react";
import api from "@/lib/api";

interface ChannelStats {
  subscriberCount: number;
  viewCount: number;
  videoCount: number;
  title: string;
}

export function useYouTube() {
  const [channelStats, setChannelStats] = useState<ChannelStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchChannelStats = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get("/api/v1/analytics/overview");
      setChannelStats(response.data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to fetch channel stats";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const syncAnalytics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.post("/api/v1/analytics/sync");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to sync analytics";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    channelStats,
    isLoading,
    error,
    fetchChannelStats,
    syncAnalytics,
  };
}
