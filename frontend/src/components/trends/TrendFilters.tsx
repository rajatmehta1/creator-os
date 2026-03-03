"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

interface TrendFiltersProps {
  onFilterChange: (filters: TrendFilterValues) => void;
  className?: string;
}

export interface TrendFilterValues {
  source: string;
  velocity: string;
  category: string;
}

const sourceOptions = [
  { value: "all", label: "All Sources" },
  { value: "google_trends", label: "Google Trends" },
  { value: "reddit", label: "Reddit" },
  { value: "youtube", label: "YouTube" },
  { value: "news", label: "News" },
];

const velocityOptions = [
  { value: "all", label: "All Velocities" },
  { value: "emerging", label: "Emerging" },
  { value: "peaking", label: "Peaking" },
  { value: "declining", label: "Declining" },
];

export default function TrendFilters({ onFilterChange, className }: TrendFiltersProps) {
  const [filters, setFilters] = useState<TrendFilterValues>({
    source: "all",
    velocity: "all",
    category: "",
  });

  function handleChange(key: keyof TrendFilterValues, value: string) {
    const updated = { ...filters, [key]: value };
    setFilters(updated);
    onFilterChange(updated);
  }

  function handleReset() {
    const reset: TrendFilterValues = { source: "all", velocity: "all", category: "" };
    setFilters(reset);
    onFilterChange(reset);
  }

  const hasActiveFilters =
    filters.source !== "all" || filters.velocity !== "all" || filters.category !== "";

  return (
    <div className={cn("flex flex-wrap items-center gap-3", className)}>
      {/* Source Filter */}
      <select
        value={filters.source}
        onChange={(e) => handleChange("source", e.target.value)}
        className="h-9 rounded-md border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
      >
        {sourceOptions.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Velocity Filter */}
      <select
        value={filters.velocity}
        onChange={(e) => handleChange("velocity", e.target.value)}
        className="h-9 rounded-md border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
      >
        {velocityOptions.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>

      {/* Category Text Input */}
      <input
        type="text"
        value={filters.category}
        onChange={(e) => handleChange("category", e.target.value)}
        placeholder="Filter by category..."
        className="h-9 w-48 rounded-md border bg-background px-3 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
      />

      {/* Reset Button */}
      {hasActiveFilters && (
        <button
          onClick={handleReset}
          className="h-9 rounded-md px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          Reset Filters
        </button>
      )}
    </div>
  );
}
