import { notFound } from "next/navigation";
import { fetchContract } from "@/lib/api";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import RiskBadge from "@/components/contracts/RiskBadge";
import { formatCurrency, formatDate, flagLabel, severityColor } from "@/lib/utils";

export const metadata = { title: "Dettaglio Appalto" };

export default async function ContractDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let contract: Awaited<ReturnType<typeof fetchContract>>;
  try {
    contract = await fetchContract(id);
  } catch {
    notFound();
  }

  const c = contract;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-start gap-4">
          <RiskBadge score={c.risk_score} />
          <div>
            <h1 className="text-2xl font-bold">{c.buyer_name}</h1>
            <p className="text-[var(--text-secondary)]">
              Fornitore: {c.supplier_name || "Non specificato"}
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Contract details */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold">Dettagli Contratto</h2>
          <dl className="space-y-3 text-sm">
            {[
              ["OCID", c.ocid],
              ["Importo aggiudicato", formatCurrency(c.amount_awarded)],
              ["Importo originale", formatCurrency(c.amount_original)],
              ["Procedura", c.procedure_type],
              ["Codice CPV", c.cpv_code],
              ["Data pubblicazione", formatDate(c.publication_date)],
              ["Data aggiudicazione", formatDate(c.award_date)],
              ["Durata (giorni)", c.contract_duration_days?.toString()],
              ["N. offerte", c.n_bids?.toString()],
              ["Regione", c.buyer_region],
              ["Provincia", c.buyer_province],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between">
                <dt className="text-[var(--text-secondary)]">{label}</dt>
                <dd className="font-medium">{value || "—"}</dd>
              </div>
            ))}
          </dl>
        </Card>

        {/* Anomaly flags */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold">
            Red Flag ({c.anomaly_flags.length})
          </h2>
          {c.anomaly_flags.length === 0 ? (
            <p className="text-sm text-[var(--text-secondary)]">
              Nessuna anomalia rilevata per questo contratto.
            </p>
          ) : (
            <div className="space-y-3">
              {c.anomaly_flags.map((flag, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-[var(--border)] p-3"
                >
                  <div className="flex items-center gap-2">
                    <Badge className={severityColor(flag.severity)}>
                      {flag.severity || "info"}
                    </Badge>
                    <span className="font-medium text-sm">{flagLabel(flag.flag_type)}</span>
                  </div>
                  {flag.ml_anomaly_score != null && (
                    <p className="mt-1 text-xs text-[var(--text-secondary)]">
                      ML anomaly score: {(flag.ml_anomaly_score * 100).toFixed(1)}%
                    </p>
                  )}
                  {flag.details && (
                    <pre className="mt-2 rounded bg-gray-50 p-2 text-xs dark:bg-gray-800 overflow-x-auto">
                      {JSON.stringify(flag.details, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      {c.source_url && (
        <p className="mt-6 text-xs text-[var(--text-secondary)]">
          Fonte:{" "}
          <a href={c.source_url} target="_blank" rel="noopener noreferrer" className="underline">
            {c.source_url}
          </a>
        </p>
      )}
    </div>
  );
}
