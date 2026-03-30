import Link from "next/link";
import { fetchPoliticians } from "@/lib/api";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import PoliticiFilterBar from "./FilterBar";

export const metadata = { title: "Politici" };

interface Props {
  searchParams: Promise<{ [key: string]: string | undefined }>;
}

export default async function PoliticiPage({ searchParams }: Props) {
  const params = await searchParams;
  let politicians: Awaited<ReturnType<typeof fetchPoliticians>> = [];

  try {
    politicians = await fetchPoliticians({
      party: params.party,
      chamber: params.chamber,
      region: params.region,
      q: params.q,
      page: params.page ? Number(params.page) : 1,
    });
  } catch {
    // API non disponibile
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">Politici</h1>

      <PoliticiFilterBar
        currentParty={params.party}
        currentChamber={params.chamber}
        currentRegion={params.region}
        currentQ={params.q}
      />

      {politicians.length === 0 ? (
        <EmptyState
          title="Nessun politico trovato"
          message="Prova a modificare i filtri di ricerca o ingesta i dati parlamentari."
        />
      ) : (
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {politicians.map((p) => (
            <Link key={p.id} href={`/politici/${p.id}`}>
              <Card className="group h-full transition-shadow hover:shadow-md">
                <div className="flex items-start gap-4">
                  {/* Avatar */}
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary-100 text-primary-700 font-bold dark:bg-primary-900/30 dark:text-primary-300">
                    {p.full_name
                      .split(" ")
                      .map((w) => w[0])
                      .slice(0, 2)
                      .join("")}
                  </div>
                  <div className="min-w-0">
                    <p className="font-semibold truncate group-hover:text-primary-600 dark:group-hover:text-primary-400">
                      {p.full_name}
                    </p>
                    <div className="mt-1 flex flex-wrap gap-2">
                      {p.current_party && (
                        <Badge className="bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
                          {p.current_party}
                        </Badge>
                      )}
                      {p.current_chamber && (
                        <Badge className="bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                          {p.current_chamber === "camera" ? "Camera" : "Senato"}
                        </Badge>
                      )}
                      {p.region && (
                        <span className="text-xs text-[var(--text-secondary)]">{p.region}</span>
                      )}
                    </div>
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
