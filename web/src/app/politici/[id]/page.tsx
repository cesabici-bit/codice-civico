import { notFound } from "next/navigation";
import { fetchPoliticianDossier } from "@/lib/api";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import RiskBadge from "@/components/contracts/RiskBadge";
import ContractStatus from "@/components/contracts/ContractStatus";
import PromiseBreakdown from "@/components/charts/PromiseBreakdown";
import AssetTimeline from "@/components/charts/AssetTimeline";
import {
  formatDate,
  formatCurrency,
  formatPercent,
  promiseStatusColor,
  promiseStatusLabel,
  voteColor,
  initials,
  coherenceColor,
} from "@/lib/utils";
import type { PoliticianDossier } from "@/lib/types";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const d = await fetchPoliticianDossier(id);
    return { title: d.full_name };
  } catch {
    return { title: "Politico" };
  }
}

export default async function PoliticianDossierPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let dossier: PoliticianDossier;
  try {
    dossier = await fetchPoliticianDossier(id);
  } catch {
    notFound();
  }

  const d = dossier;

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Header */}
      <div className="mb-8 flex flex-col gap-6 sm:flex-row sm:items-start">
        {/* Avatar */}
        <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-primary-100 text-2xl font-bold text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
          {initials(d.full_name)}
        </div>

        <div className="flex-1">
          <h1 className="text-3xl font-bold">{d.full_name}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            {d.current_party && (
              <Badge className="bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                {d.current_party}
              </Badge>
            )}
            {d.current_chamber && (
              <Badge className="bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                {d.current_chamber === "camera" ? "Camera dei Deputati" : "Senato della Repubblica"}
              </Badge>
            )}
            {d.region && (
              <Badge className="bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                {d.region}
              </Badge>
            )}
          </div>
          {d.birth_date && (
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Nato/a il {formatDate(d.birth_date)}
            </p>
          )}
        </div>
      </div>

      {/* Score cards */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="text-center">
          <p className={`text-3xl font-bold ${coherenceColor(d.coherence_score)}`}>
            {d.coherence_score != null ? `${Math.round(d.coherence_score)}%` : "—"}
          </p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">Coerenza</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-600 dark:text-primary-400">
            {d.attendance_rate != null ? formatPercent(d.attendance_rate) : "—"}
          </p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">Presenza</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold">{d.total_votes}</p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">Votazioni</p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold">{d.total_promises}</p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">Promesse</p>
        </Card>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Promise breakdown */}
        {d.total_promises > 0 && (
          <Card>
            <h2 className="mb-4 text-lg font-semibold">Promesse</h2>
            <div className="mb-4 flex gap-4 text-sm">
              <span className="text-emerald-600">{d.promises_kept} mantenute</span>
              <span className="text-red-600">{d.promises_broken} disattese</span>
              <span className="text-amber-600">{d.promises_pending} in sospeso</span>
            </div>
            <PromiseBreakdown
              kept={d.promises_kept}
              broken={d.promises_broken}
              pending={d.promises_pending}
            />
          </Card>
        )}

        {/* Asset timeline */}
        {d.asset_timeline.length > 0 && (
          <Card>
            <h2 className="mb-4 text-lg font-semibold">Patrimonio nel Tempo</h2>
            <AssetTimeline data={d.asset_timeline} />
          </Card>
        )}
      </div>

      {/* Promises list */}
      {d.promises.length > 0 && (
        <Card className="mt-8">
          <h2 className="mb-4 text-lg font-semibold">Ultime Promesse</h2>
          <div className="space-y-3">
            {d.promises.map((p) => (
              <div
                key={p.id}
                className="flex items-start gap-3 rounded-lg border border-[var(--border)] p-3"
              >
                <Badge className={promiseStatusColor(p.status)}>
                  {promiseStatusLabel(p.status)}
                </Badge>
                <div className="min-w-0">
                  <p className="text-sm">{p.sentence}</p>
                  <div className="mt-1 flex gap-2 text-xs text-[var(--text-secondary)]">
                    {p.topic && <span>{p.topic}</span>}
                    {p.specificity_score != null && (
                      <span>Specificita: {(p.specificity_score * 100).toFixed(0)}%</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Recent votes */}
      {d.recent_votes.length > 0 && (
        <Card className="mt-8">
          <h2 className="mb-4 text-lg font-semibold">Votazioni Recenti</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-[var(--text-secondary)]">
                  <th className="pb-2 font-medium">Data</th>
                  <th className="pb-2 font-medium">Oggetto</th>
                  <th className="pb-2 font-medium text-center">Voto</th>
                </tr>
              </thead>
              <tbody>
                {d.recent_votes.map((v) => (
                  <tr key={v.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="py-2 whitespace-nowrap">{formatDate(v.session_date)}</td>
                    <td className="py-2">{v.subject}</td>
                    <td className="py-2 text-center">
                      <Badge className={voteColor(v.vote_value)}>
                        {v.vote_value || "—"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Linked contracts */}
      {d.linked_contracts.length > 0 && (
        <Card className="mt-8">
          <h2 className="mb-4 text-lg font-semibold">Appalti Collegati</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-[var(--text-secondary)]">
                  <th className="pb-2 font-medium">Ente</th>
                  <th className="pb-2 font-medium">Fornitore</th>
                  <th className="pb-2 font-medium text-right">Importo</th>
                  <th className="pb-2 font-medium text-center">Rischio</th>
                </tr>
              </thead>
              <tbody>
                {d.linked_contracts.map((c) => (
                  <tr key={c.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="py-2">{c.buyer_name}</td>
                    <td className="py-2 text-[var(--text-secondary)]">{c.supplier_name || "—"}</td>
                    <td className="py-2 text-right">
                      <ContractStatus
                        amountAwarded={c.amount_awarded}
                        amountOriginal={c.amount_original}
                      />
                    </td>
                    <td className="py-2 text-center"><RiskBadge score={c.risk_score} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Sponsored laws */}
      {d.legislative_acts_sponsored.length > 0 && (
        <Card className="mt-8">
          <h2 className="mb-4 text-lg font-semibold">Atti Legislativi</h2>
          <div className="space-y-2">
            {d.legislative_acts_sponsored.map((law) => (
              <div key={law.id} className="rounded-lg border border-[var(--border)] p-3">
                <p className="font-medium">{law.title}</p>
                <p className="text-sm text-[var(--text-secondary)]">
                  {law.act_type} &middot; {law.status} &middot; {formatDate(law.presentation_date)}
                </p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Data sources */}
      <div className="mt-8 text-xs text-[var(--text-secondary)]">
        <p>Fonti dati: {d.data_sources.join(", ")}</p>
        <p>Generato il {formatDate(d.generated_at)}</p>
      </div>
    </div>
  );
}
