import { fetchAnomalyCalibration } from "@/lib/api";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";

export const metadata = { title: "Calibrazione Anomalie" };

const RULE_LABELS: Record<string, { label: string; source: string }> = {
  SPLIT_CONTRACTS: {
    label: "Frazionamento artificioso",
    source:
      "Cluster di contratti sub-soglia (<40k) dello stesso ente con stesso CPV-8 in 90gg. Soppresso se fornitori >60% diversi o cluster >20 (procurement ordinario). ANAC Rapporto 2023.",
  },
  PRICE_SPIKE: {
    label: "Prezzo anomalo",
    source:
      "Importo a >3 deviazioni standard dal log(amount) medio del bucket CPV-8 (~p99.87). Richiede min 30 contratti nel bucket. OECD 2016.",
  },
  SINGLE_BID: {
    label: "Bando a offerente unico",
    source:
      "Contratto con una sola offerta valida. Indicatore EU Single Market Scoreboard.",
  },
  LAST_MINUTE: {
    label: "Scadenza affrettata",
    source:
      "Termine ricezione offerte <15gg dalla pubblicazione. Limita la concorrenza (Dir. 2014/24/EU art.27-28).",
  },
  SHORT_DURATION: {
    label: "Esecuzione lampo",
    source:
      "Contratto sopra-soglia eseguito in <30gg. Indica possibili accordi pregressi.",
  },
  REVOLVING_DOOR: {
    label: "Fornitore ricorrente",
    source:
      "Un fornitore aggiudica >50% dei contratti di un ente. Concentrazione sospetta (ANAC 2023).",
  },
  EXTENSION_ABUSE: {
    label: "Proroghe ripetute",
    source:
      "Contratto prolungato 2+ volte oltre il termine originale.",
  },
};

function formatThresholdKey(k: string): string {
  return k
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default async function CalibrazionePage() {
  let data: Awaited<ReturnType<typeof fetchAnomalyCalibration>> | null = null;

  try {
    data = await fetchAnomalyCalibration();
  } catch {
    data = null;
  }

  if (!data) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-8">
        <EmptyState
          title="Dati calibrazione non disponibili"
          message="Esegui `codicecivico train --model anomaly` per popolare."
        />
      </div>
    );
  }

  const totalFlags = data.rules.reduce((s, r) => s + r.total_flags, 0);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-bold">Calibrazione Anomalie</h1>
      <p className="mb-6 text-[var(--text-secondary)]">
        Trasparenza sul comportamento del detector: quanti contratti sono
        flaggati per regola, con quali soglie, e cosa significa ogni regola.
      </p>

      {/* Overview */}
      <section className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card className="text-center">
          <p className="text-3xl font-bold text-primary-600 dark:text-primary-400">
            {data.total_contracts.toLocaleString("it-IT")}
          </p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Contratti analizzati
          </p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">
            {data.flagged_pct.toFixed(1)}%
          </p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Flaggati ({data.flagged_contracts.toLocaleString("it-IT")})
          </p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-red-600 dark:text-red-400">
            {data.contracts_high_risk.toLocaleString("it-IT")}
          </p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Alto rischio (≥70)
          </p>
        </Card>
        <Card className="text-center">
          <p className="text-3xl font-bold text-orange-500 dark:text-orange-400">
            {data.contracts_medium_risk.toLocaleString("it-IT")}
          </p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            Medio rischio (40-70)
          </p>
        </Card>
      </section>

      {/* Rules breakdown */}
      <section className="mb-8">
        <h2 className="mb-4 text-xl font-bold">Composizione per regola</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] text-left text-[var(--text-secondary)]">
                <th className="pb-2 font-medium">Regola</th>
                <th className="pb-2 font-medium text-right">Totale flag</th>
                <th className="pb-2 font-medium text-right">% contratti</th>
                <th className="pb-2 font-medium text-right">High</th>
                <th className="pb-2 font-medium text-right">Medium</th>
                <th className="pb-2 font-medium text-right">Low</th>
              </tr>
            </thead>
            <tbody>
              {data.rules.map((r) => {
                const meta = RULE_LABELS[r.flag_type];
                return (
                  <tr
                    key={r.flag_type}
                    className="border-b border-[var(--border)] last:border-0 align-top"
                  >
                    <td className="py-3">
                      <p className="font-medium">
                        {meta?.label || r.flag_type}
                      </p>
                      <p className="mt-0.5 text-xs text-[var(--text-secondary)]">
                        {meta?.source}
                      </p>
                    </td>
                    <td className="py-3 text-right font-mono">
                      {r.total_flags.toLocaleString("it-IT")}
                    </td>
                    <td className="py-3 text-right font-mono">
                      {r.pct_of_contracts.toFixed(2)}%
                    </td>
                    <td className="py-3 text-right font-mono text-red-600 dark:text-red-400">
                      {r.severity_high.toLocaleString("it-IT")}
                    </td>
                    <td className="py-3 text-right font-mono text-amber-600 dark:text-amber-400">
                      {r.severity_medium.toLocaleString("it-IT")}
                    </td>
                    <td className="py-3 text-right font-mono text-[var(--text-secondary)]">
                      {r.severity_low.toLocaleString("it-IT")}
                    </td>
                  </tr>
                );
              })}
              <tr className="font-semibold">
                <td className="pt-3">Totale</td>
                <td className="pt-3 text-right font-mono">
                  {totalFlags.toLocaleString("it-IT")}
                </td>
                <td colSpan={4}></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Thresholds */}
      <section>
        <h2 className="mb-4 text-xl font-bold">Soglie attive</h2>
        <p className="mb-4 text-sm text-[var(--text-secondary)]">
          Le soglie sono calibrate empiricamente contro il dataset ANAC 2025-12
          (170k contratti) per mantenere il tasso di falsi positivi plausibile
          rispetto ai base rate ANAC/OECD/EU. Regressioni sono protette da test
          automatici (<code>test_anomaly_calibration.py</code>).
        </p>
        <Card>
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {Object.entries(data.thresholds).map(([k, v]) => (
              <div
                key={k}
                className="flex justify-between border-b border-[var(--border)] pb-2 last:border-0"
              >
                <dt className="text-sm text-[var(--text-secondary)]">
                  {formatThresholdKey(k)}
                </dt>
                <dd className="text-sm font-mono">{String(v)}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </section>
    </div>
  );
}
