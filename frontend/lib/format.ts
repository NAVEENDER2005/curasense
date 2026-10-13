export function formatCurrency(value: string | number): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  return n.toLocaleString("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDate(value: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(value: string | null): string {
  if (!value) return "-";
  return new Date(value).toLocaleString("en-US", { year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
