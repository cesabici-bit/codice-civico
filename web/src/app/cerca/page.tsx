import Link from "next/link";
import { fetchSearch } from "@/lib/api";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";

export const metadata = { title: "Cerca" };

const TYPE_LABELS: Record<string, string> = {
  politician: "Politico",
  contract: "Appalto",
  law: "Legge",
  tribunal: "Tribunale",
};

const TYPE_LINKS: Record<string, string> = {
  politician: "/politici",
  contract: "/appalti",
  law: "/leggi",
  tribunal: "/giustizia",
};

interface Props {
  searchParams: Promise<{ [key: string]: string | undefined }>;
}

export default async function CercaPage({ searchParams }: Props) {
  const params = await searchParams;
  const q = params.q || "";

  let results: Awaited<ReturnType<typeof fetchSearch>> = [];
  if (q.length >= 2) {
    try {
      results = await fetchSearch(q, params.type);
    } catch {
      // API non disponibile
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-bold">
        Risultati per &quot;{q}&quot;
      </h1>
      <p className="mb-6 text-sm text-[var(--text-secondary)]">
        {results.length} risultati trovati
      </p>

      {results.length === 0 ? (
        <EmptyState
          title="Nessun risultato"
          message={
            q.length < 2
              ? "Inserisci almeno 2 caratteri per cercare."
              : "Prova con termini diversi."
          }
        />
      ) : (
        <div className="space-y-3">
          {results.map((r) => (
            <Link
              key={r.entity_id}
              href={`${TYPE_LINKS[r.entity_type] || ""}/${r.entity_id}`}
            >
              <Card className="transition-shadow hover:shadow-md">
                <div className="flex items-start gap-3">
                  <Badge className="shrink-0 bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                    {TYPE_LABELS[r.entity_type] || r.entity_type}
                  </Badge>
                  <div className="min-w-0">
                    <p className="font-medium">{r.title}</p>
                    {r.snippet && (
                      <p className="mt-1 text-sm text-[var(--text-secondary)] truncate">
                        {r.snippet}
                      </p>
                    )}
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
