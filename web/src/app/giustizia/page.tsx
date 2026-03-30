import Link from "next/link";
import { fetchCourtRankings } from "@/lib/api";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import ItalyMapWrapper from "@/components/map/ItalyMapWrapper";
import MetricSelector from "./MetricSelector";

export const metadata = { title: "Mappa della Giustizia" };

interface Props {
  searchParams: Promise<{ [key: string]: string | undefined }>;
}

export default async function GiustiziaPage({ searchParams }: Props) {
  const params = await searchParams;
  const metric = params.metric || "disposition_time";

  let rankings: Awaited<ReturnType<typeof fetchCourtRankings>> = [];
  try {
    rankings = await fetchCourtRankings({
      metric,
      limit: 200,
      order: metric === "clearance_rate" ? "desc" : "asc",
    });
  } catch {
    // API non disponibile
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-bold">Mappa della Giustizia</h1>
      <p className="mb-6 text-[var(--text-secondary)]">
        Performance di 143 tribunali italiani — durata media, clearance rate, cause pendenti.
      </p>

      <MetricSelector current={metric} />

      {rankings.length === 0 ? (
        <EmptyState
          title="Nessun dato disponibile"
          message="I dati del Ministero della Giustizia non sono ancora stati ingeriti."
        />
      ) : (
        <>
          <div className="mt-6">
            <ItalyMapWrapper rankings={rankings} />
          </div>

          {/* Rankings table */}
          <Card className="mt-8">
            <h2 className="mb-4 text-lg font-semibold">
              Classifica Tribunali
              <span className="ml-2 text-sm font-normal text-[var(--text-secondary)]">
                ({rankings.length} tribunali)
              </span>
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[var(--text-secondary)]">
                    <th className="pb-2 font-medium w-12">#</th>
                    <th className="pb-2 font-medium">Tribunale</th>
                    <th className="pb-2 font-medium">Regione</th>
                    <th className="pb-2 font-medium text-right">Valore</th>
                  </tr>
                </thead>
                <tbody>
                  {rankings.map((r, i) => (
                    <tr key={r.name} className="border-b border-[var(--border)] last:border-0">
                      <td className="py-2 text-[var(--text-secondary)]">{i + 1}</td>
                      <td className="py-2 font-medium">{r.name}</td>
                      <td className="py-2 text-[var(--text-secondary)]">{r.region || "—"}</td>
                      <td className="py-2 text-right font-mono">
                        {r.metric_value?.toFixed(1) ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
