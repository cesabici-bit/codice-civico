import { notFound } from "next/navigation";
import { fetchLaw } from "@/lib/api";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import { formatDate } from "@/lib/utils";

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const law = await fetchLaw(id);
    return { title: law.title };
  } catch {
    return { title: "Legge" };
  }
}

export default async function LawDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let law: Awaited<ReturnType<typeof fetchLaw>>;
  try {
    law = await fetchLaw(id);
  } catch {
    notFound();
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8">
      <h1 className="mb-2 text-2xl font-bold">{law.title}</h1>
      <div className="mb-6 flex flex-wrap gap-2 text-sm text-[var(--text-secondary)]">
        {law.act_type && <span>{law.act_type}</span>}
        {law.chamber && <span>&middot; {law.chamber}</span>}
        {law.presentation_date && <span>&middot; {formatDate(law.presentation_date)}</span>}
        {law.status && (
          <Badge className="bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300">
            {law.status}
          </Badge>
        )}
      </div>

      {/* AI Translation */}
      {law.plain_translation ? (
        <Card className="mb-8">
          <div className="mb-3 flex items-center gap-2">
            <svg className="h-5 w-5 text-accent-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
            <h2 className="text-lg font-semibold">Traduzione in Linguaggio Semplice</h2>
          </div>
          <div className="prose dark:prose-invert max-w-none text-sm">
            {Object.entries(law.plain_translation).map(([key, value]) => (
              <div key={key} className="mb-4">
                <h3 className="text-sm font-semibold capitalize text-primary-700 dark:text-primary-400">
                  {key.replace(/_/g, " ")}
                </h3>
                <p className="text-[var(--text-secondary)]">{String(value)}</p>
              </div>
            ))}
          </div>
          {law.translated_at && (
            <p className="mt-3 text-xs text-[var(--text-secondary)]">
              Tradotto il {formatDate(law.translated_at)}
            </p>
          )}
        </Card>
      ) : (
        <Card className="mb-8">
          <p className="text-sm text-[var(--text-secondary)]">
            Traduzione AI non ancora disponibile per questo atto.
            La traduzione viene generata automaticamente tramite LLaMAntino.
          </p>
        </Card>
      )}

      {/* Full text */}
      {law.full_text && (
        <Card>
          <h2 className="mb-4 text-lg font-semibold">Testo Integrale</h2>
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--text-secondary)]">
            {law.full_text}
          </div>
        </Card>
      )}

      {law.source_uri && (
        <p className="mt-6 text-xs text-[var(--text-secondary)]">
          Fonte:{" "}
          <a href={law.source_uri} target="_blank" rel="noopener noreferrer" className="underline">
            {law.source_uri}
          </a>
        </p>
      )}
    </div>
  );
}
