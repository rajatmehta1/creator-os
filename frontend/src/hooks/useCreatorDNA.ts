"use client";

import { useCallback, useState } from "react";
import api from "@/lib/api";
import type { CreatorDNA } from "@/types/user";

export function useCreatorDNA() {
  const [dna, setDNA] = useState<CreatorDNA | null>(null);
  const [buildStatus, setBuildStatus] = useState<{
    status: string;
    progress: number;
    message: string;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDNA = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.get("/api/v1/profile/dna");
      setDNA(response.data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to fetch DNA";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const buildDNA = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      await api.post("/api/v1/profile/dna/build");
      setBuildStatus({ status: "queued", progress: 0, message: "Build queued" });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to start DNA build";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const checkBuildStatus = useCallback(async () => {
    try {
      const response = await api.get("/api/v1/profile/dna/status");
      setBuildStatus(response.data);
      if (response.data.status === "completed") {
        await fetchDNA();
      }
    } catch {
      // Silently fail status checks
    }
  }, [fetchDNA]);

  return {
    dna,
    buildStatus,
    isLoading,
    error,
    fetchDNA,
    buildDNA,
    checkBuildStatus,
  };
}
