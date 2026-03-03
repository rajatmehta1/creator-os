"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { cn } from "@/lib/utils";

interface TrendTimelineProps {
  data: Array<{ date: string; score: number }>;
  title: string;
  className?: string;
}

export default function TrendTimeline({ data, title, className }: TrendTimelineProps) {
  if (data.length === 0) {
    return (
      <div className={cn("rounded-lg border bg-card p-6", className)}>
        <h3 className="text-sm font-semibold">{title}</h3>
        <div className="mt-4 flex h-48 items-center justify-center">
          <p className="text-sm text-muted-foreground">No timeline data available</p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("rounded-lg border bg-card p-6", className)}>
      <h3 className="text-sm font-semibold">{title}</h3>
      <div className="mt-4 h-48">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              className="text-muted-foreground"
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11 }}
              className="text-muted-foreground"
              tickLine={false}
              axisLine={false}
              width={30}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelStyle={{ color: "hsl(var(--muted-foreground))" }}
            />
            <Line
              type="monotone"
              dataKey="score"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={{ r: 3, fill: "hsl(var(--primary))" }}
              activeDot={{ r: 5, fill: "hsl(var(--primary))" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
