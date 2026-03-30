import Link from "next/link";
import { fetchLaws } from "@/lib/api";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";

export const metadata = { title: "Leggi" };

interface Props {
  searchParams: Promise<{ [key: string]: string | undefined }>;
}

export default async function LeggiPage({ searchParams }: Props) {
  const params = await searchParams;
  let laws: Awaited<ReturnType<typeof fetchLaws>> = [];

  try {
    laws = await fetchLaws({
      chamber: params.chamber,
      status: params.status,
      page: params.page ? Number(params.page) : 1,
    });
  } catch {
    // API non disponibile
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">Atti Legislativi</h1>

      {laws.length === 0 ? (
        <EmptyState
          title="Nessun atto trovato"
          message="I dati legislativi non sono ancora stati ingeriti."
        />
      ) : (
        <div className="space-y-3">
          {laws.map((law) => (
            <Link key={law.id} href={`/leggi/${law.id}`}>
              <Card className="transition-shadow hover:shadow-md">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="font-medium">{law.title}</p>
                    <div className="mt-1 flex flex-wrap gap-2 text-sm text-[var(--text-secondary)]">
                      {law.act_type && <span>{law.act_type}</span>}
                      {law.chamber && <span>&middot; {law.chamber}</span>}
                      {law.presentation_date && (
                        <span>&middot; {formatDate(law.presentation_date)}</span>
                      )}
                    </div>
                  </div>
                  {law.status && (
                    <Badge className="shrink-0 bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                      {law.status}
                    </Badge>
                  )}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
