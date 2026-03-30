"use client";

interface ScoreGaugeProps {
  value: number | null;
  label: string;
  maxValue?: number;
  size?: number;
}

export default function ScoreGauge({
  value,
  label,
  maxValue = 100,
  size = 120,
}: ScoreGaugeProps) {
  const pct = value != null ? Math.min(value / maxValue, 1) : 0;
  const circumference = 2 * Math.PI * 45;
  const offset = circumference * (1 - pct);

  const color =
    value == null
      ? "#9ca3af"
      : value >= 70
        ? "#22c55e"
        : value >= 40
          ? "#eab308"
          : "#ef4444";

  return (
    <div className="flex flex-col items-center gap-1">
      <svg width={size} height={size} viewBox="0 0 100 100" className="-rotate-90">
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke="currentColor"
          className="text-gray-200 dark:text-gray-700"
          strokeWidth="8"
        />
        <circle
          cx="50"
          cy="50"
          r="45"
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-2xl font-bold" style={{ color }}>
          {value != null ? Math.round(value) : "—"}
        </span>
      </div>
      <span className="text-xs font-medium text-[var(--text-secondary)]">{label}</span>
    </div>
  );
}
