"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { REGIONS, CHAMBERS } from "@/lib/constants";
import { useDebounce } from "@/hooks/useDebounce";
import { useEffect } from "react";

interface Props {
  currentParty?: string;
  currentChamber?: string;
  currentRegion?: string;
  currentQ?: string;
}

export default function PoliticiFilterBar({
  currentParty,
  currentChamber,
  currentRegion,
  currentQ,
}: Props) {
  const router = useRouter();
  const [q, setQ] = useState(currentQ || "");
  const debouncedQ = useDebounce(q, 400);

  function buildUrl(overrides: Record<string, string | undefined>) {
    const params = new URLSearchParams();
    const merged = {
      party: currentParty,
      chamber: currentChamber,
      region: currentRegion,
      q: debouncedQ || undefined,
      ...overrides,
    };
    Object.entries(merged).forEach(([k, v]) => {
      if (v) params.set(k, v);
    });
    const qs = params.toString();
    return `/politici${qs ? `?${qs}` : ""}`;
  }

  useEffect(() => {
    router.push(buildUrl({ q: debouncedQ || undefined }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedQ]);

  return (
    <div className="flex flex-wrap gap-3">
      {/* Search */}
      <input
        type="text"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Cerca per nome..."
        className="rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 text-sm outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500"
      />

      {/* Chamber */}
      <select
        value={currentChamber || ""}
        onChange={(e) => router.push(buildUrl({ chamber: e.target.value || undefined }))}
        className="rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
      >
        <option value="">Tutte le camere</option>
        {CHAMBERS.map((c) => (
          <option key={c.value} value={c.value}>
            {c.label}
          </option>
        ))}
      </select>

      {/* Region */}
      <select
        value={currentRegion || ""}
        onChange={(e) => router.push(buildUrl({ region: e.target.value || undefined }))}
        className="rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 text-sm"
      >
        <option value="">Tutte le regioni</option>
        {REGIONS.map((r) => (
          <option key={r} value={r}>
            {r}
          </option>
        ))}
      </select>

      {/* Clear filters */}
      {(currentParty || currentChamber || currentRegion || currentQ) && (
        <button
          onClick={() => router.push("/politici")}
          className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm text-[var(--text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          Cancella filtri
        </button>
      )}
    </div>
  );
}
