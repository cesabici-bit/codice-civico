import { formatCurrency } from "@/lib/utils";

interface ContractStatusProps {
  amountAwarded: number | null | undefined;
  amountOriginal: number | null | undefined;
  /** Layout: "inline" = single line, "stacked" = amount on top, status label below. */
  variant?: "inline" | "stacked";
}

/**
 * Renders the awarded amount when known, otherwise an "In corso" badge
 * (the procurement is still open / not yet awarded by ANAC).
 * Falls back to the base-auction amount as a parenthetical hint when the
 * contract is still in corso, so the user sees some value instead of a dash.
 */
export default function ContractStatus({
  amountAwarded,
  amountOriginal,
  variant = "stacked",
}: ContractStatusProps) {
  const awarded = amountAwarded ?? null;
  const base = amountOriginal ?? null;

  if (awarded !== null && awarded > 0) {
    const label = (
      <span className="inline-flex items-center rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-300">
        Aggiudicato
      </span>
    );
    if (variant === "inline") {
      return (
        <span className="inline-flex items-center gap-2">
          <span className="font-medium">{formatCurrency(awarded)}</span>
          {label}
        </span>
      );
    }
    return (
      <div className="flex flex-col items-end">
        <span className="font-medium">{formatCurrency(awarded)}</span>
        <span className="mt-0.5">{label}</span>
      </div>
    );
  }

  // Not yet awarded
  const inCorsoBadge = (
    <span className="inline-flex items-center rounded-full bg-sky-100 dark:bg-sky-900/30 px-2 py-0.5 text-[10px] font-medium text-sky-700 dark:text-sky-300">
      In corso
    </span>
  );
  const baseLabel = base && base > 0 ? formatCurrency(base) : "—";

  if (variant === "inline") {
    return (
      <span className="inline-flex items-center gap-2">
        <span className="text-[var(--text-secondary)]">{baseLabel}</span>
        {inCorsoBadge}
      </span>
    );
  }
  return (
    <div className="flex flex-col items-end">
      <span className="text-[var(--text-secondary)]">{baseLabel}</span>
      <span className="mt-0.5" title="Base d'asta — gara non ancora aggiudicata">
        {inCorsoBadge}
      </span>
    </div>
  );
}
