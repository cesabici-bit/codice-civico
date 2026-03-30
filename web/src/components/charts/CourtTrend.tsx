"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { CourtStatResponse } from "@/lib/types";

interface Props {
  data: CourtStatResponse[];
}

export default function CourtTrend({ data }: Props) {
  if (data.length === 0) return null;

  const formatted = data.map((s) => ({
    ...s,
    period: s.period.slice(0, 7), // YYYY-MM
  }));

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={formatted}>
          <XAxis dataKey="period" />
          <YAxis />
          <Tooltip
            contentStyle={{
              borderRadius: "8px",
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg-card)",
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="avg_duration_days"
            name="Durata media (gg)"
            stroke="#ef4444"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="clearance_rate"
            name="Clearance rate"
            stroke="#22c55e"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="pending_cases"
            name="Pendenti"
            stroke="#eab308"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
