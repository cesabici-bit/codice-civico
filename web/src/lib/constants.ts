// Italian regions and labels for the frontend

export const REGIONS = [
  "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
  "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
  "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana",
  "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto",
] as const;

export const CHAMBERS = [
  { value: "camera", label: "Camera dei Deputati" },
  { value: "senato", label: "Senato della Repubblica" },
] as const;

export const COURT_METRICS = [
  { value: "disposition_time", label: "Durata media (giorni)" },
  { value: "clearance_rate", label: "Clearance rate" },
  { value: "pending_cases", label: "Cause pendenti" },
  { value: "new_cases", label: "Nuove cause" },
  { value: "resolved_cases", label: "Cause risolte" },
] as const;

export const PROMISE_STATUSES = [
  { value: "kept", label: "Mantenute" },
  { value: "broken", label: "Disattese" },
  { value: "pending", label: "In sospeso" },
  { value: "ambiguous", label: "Ambigue" },
] as const;

export const LAW_STATUSES = [
  { value: "presentato", label: "Presentato" },
  { value: "in commissione", label: "In Commissione" },
  { value: "approvato", label: "Approvato" },
  { value: "ritirato", label: "Ritirato" },
] as const;

export const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/politici", label: "Politici" },
  { href: "/appalti", label: "Appalti" },
  { href: "/giustizia", label: "Giustizia" },
  { href: "/leggi", label: "Leggi" },
] as const;

/** Choropleth color scale (green to red, 7 stops) */
export const CHOROPLETH_COLORS = [
  "#22c55e", // green-500
  "#84cc16", // lime-500
  "#eab308", // yellow-500
  "#f97316", // orange-500
  "#ef4444", // red-500
] as const;

/** Reverse scale (red to green) for clearance_rate */
export const CHOROPLETH_COLORS_REVERSE = [
  "#ef4444",
  "#f97316",
  "#eab308",
  "#84cc16",
  "#22c55e",
] as const;
