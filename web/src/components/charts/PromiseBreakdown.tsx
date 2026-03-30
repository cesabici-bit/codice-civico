"use client";

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface Props {
  kept: number;
  broken: number;
  pending: number;
}

const COLORS = { kept: "#22c55e", broken: "#ef4444", pending: "#eab308" };
const LABELS = { kept: "Mantenute", broken: "Disattese", pending: "In sospeso" };

export default function PromiseBreakdown({ kept, broken, pending }: Props) {
  const data = [
    { name: LABELS.kept, value: kept, color: COLORS.kept },
    { name: LABELS.broken, value: broken, color: COLORS.broken },
    { name: LABELS.pending, value: pending, color: COLORS.pending },
  ].filter((d) => d.value > 0);

  if (data.length === 0) return null;

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => [value, "Promesse"]}
            contentStyle={{
              borderRadius: "8px",
              border: "1px solid var(--border)",
              backgroundColor: "var(--bg-card)",
            }}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
