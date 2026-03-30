"use client";

import { useRouter } from "next/navigation";
import { COURT_METRICS } from "@/lib/constants";

interface Props {
  current: string;
}

export default function MetricSelector({ current }: Props) {
  const router = useRouter();

  return (
    <div className="flex flex-wrap gap-2">
      {COURT_METRICS.map((m) => (
        <button
          key={m.value}
          onClick={() => router.push(`/giustizia?metric=${m.value}`)}
          className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
            current === m.value
              ? "bg-primary-600 text-white"
              : "border border-[var(--border)] text-[var(--text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800"
          }`}
        >
          {m.label}
        </button>
      ))}
    </div>
  );
}
