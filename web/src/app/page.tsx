import Link from "next/link";
import Card from "@/components/ui/Card";
import RiskBadge from "@/components/contracts/RiskBadge";
import { fetchContractAnomalies, fetchLaws, fetchStatsOverview } from "@/lib/api";
import { formatCurrency, formatDate } from "@/lib/utils";

export default async function DashboardPage() {
  let stats = {
    politicians: 0,
    contracts: 0,
    high_risk_contracts: 0,
    anomaly_flags: 0,
    tribunals: 0,
    laws: 0,
  };
  let contractsTop: Awaited<ReturnType<typeof fetchContractAnomalies>> = [];
  let lawsRecent: Awaited<ReturnType<typeof fetchLaws>> = [];

  try {
    const [overview, anomalies, laws] = await Promise.allSettled([
      fetchStatsOverview(),
      fetchContractAnomalies(5),
      fetchLaws({ per_page: 5 }),
    ]);
    if (overview.status === "fulfilled") stats = { ...stats, ...overview.value };
    if (anomalies.status === "fulfilled") contractsTop = anomalies.value;
    if (laws.status === "fulfilled") lawsRecent = laws.value;
  } catch {
    // API non disponibile — mostriamo la pagina con dati vuoti
  }

  const sections = [
    {
      href: "/politici",
      title: "Politici",
      description: "Dossier, promesse, coerenza e patrimoni di deputati e senatori",
      icon: (
        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
        </svg>
      ),
    },
    {
      href: "/appalti",
      title: "Appalti",
      description: "Contratti pubblici con rilevamento anomalie e punteggio di rischio",
      icon: (
        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
        </svg>
      ),
    },
    {
      href: "/giustizia",
      title: "Giustizia",
      description: "Mappa interattiva di 143 tribunali con durate, arretrati e clearance rate",
      icon: (
        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z" />
        </svg>
      ),
    },
    {
      href: "/leggi",
      title: "Leggi",
      description: "Atti legislativi con traduzione AI in linguaggio semplice",
      icon: (
        <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
        </svg>
      ),
    },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      {/* Hero */}
      <section className="mb-12 text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          <span className="text-primary-600 dark:text-primary-400">Codice</span> Civico
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-[var(--text-secondary)]">
          Incrociamo tutti i dati pubblici italiani — parlamento, appalti, giustizia —
          e produciamo insight con l&apos;intelligenza artificiale.
          Trasparenza automatica, per tutti.
        </p>
      </section>

      {/* Stat cards */}
      <section className="mb-12 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "Politici tracciati", value: stats.politicians || "—" },
          { label: "Appalti ad alto rischio", value: stats.high_risk_contracts || "—" },
          { label: "Tribunali monitorati", value: stats.tribunals || "—" },
          { label: "Leggi analizzate", value: stats.laws || "—" },
        ].map((stat) => (
          <Card key={stat.label} className="text-center">
            <p className="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {stat.value}
            </p>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">{stat.label}</p>
          </Card>
        ))}
      </section>

      {/* Section cards */}
      <section className="mb-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {sections.map((s) => (
          <Link key={s.href} href={s.href}>
            <Card className="group h-full transition-shadow hover:shadow-md">
              <div className="mb-3 text-primary-600 dark:text-primary-400 group-hover:scale-110 transition-transform">
                {s.icon}
              </div>
              <h3 className="font-semibold">{s.title}</h3>
              <p className="mt-1 text-sm text-[var(--text-secondary)]">{s.description}</p>
            </Card>
          </Link>
        ))}
      </section>

      {/* Top anomalies */}
      {contractsTop.length > 0 && (
        <section className="mb-12">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-bold">Top Anomalie Appalti</h2>
            <Link
              href="/appalti/anomalie"
              className="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
            >
              Vedi tutte &rarr;
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] text-left text-[var(--text-secondary)]">
                  <th className="pb-2 font-medium">Ente appaltante</th>
                  <th className="pb-2 font-medium">Fornitore</th>
                  <th className="pb-2 font-medium text-right">Importo</th>
                  <th className="pb-2 font-medium text-center">Rischio</th>
                </tr>
              </thead>
              <tbody>
                {contractsTop.map((c) => (
                  <tr key={c.id} className="border-b border-[var(--border)] last:border-0">
                    <td className="py-3">
                      <Link href={`/appalti/${c.id}`} className="hover:underline font-medium">
                        {c.buyer_name}
                      </Link>
                    </td>
                    <td className="py-3 text-[var(--text-secondary)]">{c.supplier_name || "—"}</td>
                    <td className="py-3 text-right">{formatCurrency(c.amount_awarded)}</td>
                    <td className="py-3 text-center">
                      <RiskBadge score={c.risk_score} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Recent laws */}
      {lawsRecent.length > 0 && (
        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-bold">Ultime Leggi</h2>
            <Link
              href="/leggi"
              className="text-sm font-medium text-primary-600 hover:underline dark:text-primary-400"
            >
              Vedi tutte &rarr;
            </Link>
          </div>
          <div className="grid gap-3">
            {lawsRecent.map((law) => (
              <Link key={law.id} href={`/leggi/${law.id}`}>
                <Card className="transition-shadow hover:shadow-md">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="font-medium truncate">{law.title}</p>
                      <p className="text-sm text-[var(--text-secondary)]">
                        {law.act_type} &middot; {law.chamber} &middot; {formatDate(law.presentation_date)}
                      </p>
                    </div>
                    {law.status && (
                      <span className="shrink-0 rounded-full bg-primary-50 px-2.5 py-0.5 text-xs font-medium text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                        {law.status}
                      </span>
                    )}
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
