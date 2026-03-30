import { notFound } from "next/navigation";
import { fetchCourt } from "@/lib/api";
import Card from "@/components/ui/Card";
import CourtTrend from "@/components/charts/CourtTrend";
import EmptyState from "@/components/ui/EmptyState";

export const metadata = { title: "Dettaglio Tribunale" };

export default async function CourtDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let court: Awaited<ReturnType<typeof fetchCourt>>;
  try {
    court = await fetchCourt(id);
  } catch {
    notFound();
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="text-2xl font-bold">{court.name}</h1>
      <p className="text-[var(--text-secondary)]">
        {court.type} &middot; {court.region} &middot; {court.province}
      </p>

      {court.stats.length === 0 ? (
        <EmptyState
          title="Nessuna statistica disponibile"
          message="I dati per questo tribunale non sono ancora stati ingeriti."
        />
      ) : (
        <>
          <Card className="mt-8">
            <h2 className="mb-4 text-lg font-semibold">Andamento nel Tempo</h2>
            <CourtTrend data={court.stats} />
          </Card>

          <Card className="mt-8">
            <h2 className="mb-4 text-lg font-semibold">Dati Dettagliati</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[var(--text-secondary)]">
                    <th className="pb-2 font-medium">Periodo</th>
                    <th className="pb-2 font-medium">Categoria</th>
                    <th className="pb-2 font-medium text-right">Nuove</th>
                    <th className="pb-2 font-medium text-right">Risolte</th>
                    <th className="pb-2 font-medium text-right">Pendenti</th>
                    <th className="pb-2 font-medium text-right">Durata (gg)</th>
                    <th className="pb-2 font-medium text-right">Clearance</th>
                  </tr>
                </thead>
                <tbody>
                  {court.stats.map((s, i) => (
                    <tr key={i} className="border-b border-[var(--border)] last:border-0">
                      <td className="py-2">{s.period}</td>
                      <td className="py-2">{s.case_category || "—"}</td>
                      <td className="py-2 text-right">{s.new_cases ?? "—"}</td>
                      <td className="py-2 text-right">{s.resolved_cases ?? "—"}</td>
                      <td className="py-2 text-right">{s.pending_cases ?? "—"}</td>
                      <td className="py-2 text-right">{s.avg_duration_days?.toFixed(0) ?? "—"}</td>
                      <td className="py-2 text-right">{s.clearance_rate?.toFixed(2) ?? "—"}</td>
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
