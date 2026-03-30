import Link from "next/link";
import { fetchContractAnomalies } from "@/lib/api";
import Card from "@/components/ui/Card";
import RiskBadge from "@/components/contracts/RiskBadge";
import EmptyState from "@/components/ui/EmptyState";
import { formatCurrency } from "@/lib/utils";

export const metadata = { title: "Top Anomalie Appalti" };

export default async function AnomaliePage() {
  let anomalies: Awaited<ReturnType<typeof fetchContractAnomalies>> = [];

  try {
    anomalies = await fetchContractAnomalies(50);
  } catch {
    // API non disponibile
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-bold">Top Anomalie</h1>
      <p className="mb-6 text-[var(--text-secondary)]">
        Contratti pubblici con il punteggio di rischio piu alto, ordinati per probabilita di irregolarita.
      </p>

      {anomalies.length === 0 ? (
        <EmptyState
          title="Nessuna anomalia rilevata"
          message="I dati ANAC non sono ancora stati ingeriti o nessun contratto supera la soglia."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {anomalies.map((c) => (
            <Link key={c.id} href={`/appalti/${c.id}`}>
              <Card className="group h-full transition-shadow hover:shadow-md">
                <div className="mb-3 flex items-center justify-between">
                  <RiskBadge score={c.risk_score} />
                  <span className="text-xs text-[var(--text-secondary)]">
                    {c.n_bids != null ? `${c.n_bids} offerte` : "—"}
                  </span>
                </div>
                <p className="font-semibold truncate group-hover:text-primary-600 dark:group-hover:text-primary-400">
                  {c.buyer_name}
                </p>
                <p className="text-sm text-[var(--text-secondary)] truncate">
                  {c.supplier_name || "Fornitore non specificato"}
                </p>
                <p className="mt-2 text-lg font-bold">{formatCurrency(c.amount_awarded)}</p>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
