// Formatting and utility functions

export function formatCurrency(amount: number | null): string {
  if (amount == null) return "—";
  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(dateStr));
}

export function formatNumber(n: number | null): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("it-IT").format(n);
}

export function formatPercent(n: number | null): string {
  if (n == null) return "—";
  return `${n.toFixed(1)}%`;
}

/** Risk score 0-100 → color class */
export function riskColor(score: number): string {
  if (score >= 70) return "text-red-600 dark:text-red-400";
  if (score >= 40) return "text-amber-600 dark:text-amber-400";
  return "text-emerald-600 dark:text-emerald-400";
}

/** Risk score 0-100 → background color class */
export function riskBgColor(score: number): string {
  if (score >= 70) return "bg-red-100 dark:bg-red-900/30";
  if (score >= 40) return "bg-amber-100 dark:bg-amber-900/30";
  return "bg-emerald-100 dark:bg-emerald-900/30";
}

/** Promise status → badge color */
export function promiseStatusColor(status: string): string {
  switch (status) {
    case "kept":
      return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300";
    case "broken":
      return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
    case "pending":
      return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
  }
}

/** Promise status → Italian label */
export function promiseStatusLabel(status: string): string {
  switch (status) {
    case "kept": return "Mantenuta";
    case "broken": return "Disattesa";
    case "pending": return "In sospeso";
    case "ambiguous": return "Ambigua";
    default: return status;
  }
}

/** Vote value → badge color */
export function voteColor(value: string | null): string {
  switch (value) {
    case "favorevole":
      return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300";
    case "contrario":
      return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
    case "astenuto":
      return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300";
    case "assente":
      return "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
  }
}

/** Anomaly flag type → Italian label */
export function flagLabel(flagType: string): string {
  const labels: Record<string, string> = {
    SPLIT_CONTRACTS: "Frazionamento artificioso",
    SINGLE_BID: "Offerta unica",
    LAST_MINUTE: "Aggiudicazione last-minute",
    PRICE_SPIKE: "Prezzo anomalo",
    REVOLVING_DOOR: "Revolving door",
    SHORT_DURATION: "Durata sospetta",
    EXTENSION_ABUSE: "Proroghe eccessive",
  };
  return labels[flagType] || flagType;
}

/** Anomaly severity → color */
export function severityColor(severity: string | null): string {
  switch (severity) {
    case "high":
      return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300";
    case "medium":
      return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300";
    case "low":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300";
  }
}

/** Generate initials for avatar fallback */
export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

/** Coherence score color */
export function coherenceColor(score: number | null): string {
  if (score == null) return "text-gray-400";
  if (score >= 70) return "text-emerald-600 dark:text-emerald-400";
  if (score >= 40) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

/** Clamp a value between min and max */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}
