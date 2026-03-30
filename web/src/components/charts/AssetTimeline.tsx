"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { AssetTimelineEntry } from "@/lib/types";

interface Props {
  data: AssetTimelineEntry[];
}

export default function AssetTimeline({ data }: Props) {
  if (data.length === 0) return null;

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data}>
          <XAxis dataKey="year" />
          <YAxis
            tickFormatter={(v: number) =>
              new Intl.NumberFormat("it-IT", {
                notation: "compact",
                style: "currency",
                currency: "EUR",
              }).format(v)
            }
          />
          <Tooltip
            formatter={(value: number) => [
              new Intl.NumberFormat("it-IT", {
                style: "currency",
                currency: "EUR",
              }).format(value),
            ]}
            contentStyle={{
              borderRadius: "8px",
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg-card)",
            }}
          />
          <Legend />
          <Bar dataKey="total_income" name="Reddito" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          <Bar dataKey="total_assets" name="Patrimonio" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
