"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface DataPoint {
  date: string;
  views?: number;
  watchTime?: number;
  ctr?: number;
  retention?: number;
}

interface PerformanceChartProps {
  data: DataPoint[];
  metrics?: Array<"views" | "watchTime" | "ctr" | "retention">;
  title?: string;
}

const METRIC_CONFIG = {
  views: { color: "#8b5cf6", label: "Views" },
  watchTime: { color: "#06b6d4", label: "Watch Time (hrs)" },
  ctr: { color: "#10b981", label: "CTR %" },
  retention: { color: "#f59e0b", label: "Retention %" },
};

export default function PerformanceChart({
  data,
  metrics = ["views"],
  title,
}: PerformanceChartProps) {
  return (
    <div className="rounded-lg border bg-card p-6">
      {title && <h3 className="mb-4 text-sm font-semibold">{title}</h3>}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis dataKey="date" className="text-xs" />
          <YAxis className="text-xs" />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--card))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "0.5rem",
            }}
          />
          <Legend />
          {metrics.map((metric) => (
            <Line
              key={metric}
              type="monotone"
              dataKey={metric}
              stroke={METRIC_CONFIG[metric].color}
              name={METRIC_CONFIG[metric].label}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
