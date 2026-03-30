"use client";

import dynamic from "next/dynamic";
import type { TribunalRanking } from "@/lib/types";

const ItalyMap = dynamic(() => import("@/components/map/ItalyMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[500px] items-center justify-center rounded-xl border border-[var(--border)] bg-gray-50 dark:bg-gray-800">
      <p className="text-[var(--text-secondary)]">Caricamento mappa...</p>
    </div>
  ),
});

interface Props {
  rankings: TribunalRanking[];
}

export default function ItalyMapWrapper({ rankings }: Props) {
  return <ItalyMap rankings={rankings} />;
}
