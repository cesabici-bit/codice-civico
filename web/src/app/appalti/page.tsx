import Link from "next/link";
import { fetchContracts } from "@/lib/api";
import Card from "@/components/ui/Card";
import RiskBadge from "@/components/contracts/RiskBadge";
import ContractStatus from "@/components/contracts/ContractStatus";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

export const metadata = { title: "Appalti" };

interface Props {
  searchParams: Promise<{ [key: string]: string | undefined }>;
}

export default async function AppaltiPage({ searchParams }: Props) {
  const params = await searchParams;
  let contracts: Awaited<ReturnType<typeof fetchContracts>> = [];

  try {
    contracts = await fetchContracts({
      region: params.region,
      risk_min: params.risk_min ? Number(params.risk_min) : undefined,
      page: params.page ? Number(params.page) : 1,
    });
  } catch {
    // API non disponibile
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Appalti Pubblici</h1>
        <Link
          href="/appalti/anomalie"
          className="rounded-lg bg-red-50 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-300 dark:hover:bg-red-900/30"
        >
          Top Anomalie &rarr;
        </Link>
      </div>

      {contracts.length === 0 ? (
        <EmptyState
          title="Nessun contratto trovato"
          message="Prova a modificare i filtri o ingesta i dati ANAC."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--text-secondary)]">
                <th className="pb-3 font-medium">Ente appaltante</th>
                <th className="pb-3 font-medium">Fornitore</th>
                <th className="pb-3 font-medium">Procedura</th>
                <th className="pb-3 font-medium text-right">Importo</th>
                <th className="pb-3 font-medium text-center">Offerte</th>
                <th className="pb-3 font-medium text-center">Rischio</th>
                <th className="pb-3 font-medium">Data</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((c) => (
                <tr key={c.id} className="border-b border-[var(--border)] last:border-0 hover:bg-gray-50 dark:hover:bg-gray-800/50">
                  <td className="py-3">
                    <Link href={`/appalti/${c.id}`} className="font-medium hover:underline">
                      {c.buyer_name}
                    </Link>
                  </td>
                  <td className="py-3 text-[var(--text-secondary)]">{c.supplier_name || "—"}</td>
                  <td className="py-3 text-[var(--text-secondary)]">{c.procedure_type || "—"}</td>
                  <td className="py-3 text-right">
                    <ContractStatus
                      amountAwarded={c.amount_awarded}
                      amountOriginal={c.amount_original}
                    />
                  </td>
                  <td className="py-3 text-center">{c.n_bids ?? "—"}</td>
                  <td className="py-3 text-center"><RiskBadge score={c.risk_score} /></td>
                  <td className="py-3 text-[var(--text-secondary)]">{formatDate(c.award_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
