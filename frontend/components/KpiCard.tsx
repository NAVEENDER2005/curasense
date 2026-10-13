export default function KpiCard({
  label, value, sublabel, tone = "default",
}: {
  label: string;
  value: string;
  sublabel?: string;
  tone?: "default" | "risk" | "good";
}) {
  const valueColor = tone === "risk" ? "text-risk-high" : tone === "good" ? "text-risk-low" : "text-ink";
  return (
    <div className="rounded-xl border border-hairline bg-surface p-5">
      <div className="text-sm font-medium text-ink-secondary">{label}</div>
      <div className={`mt-2 text-3xl font-semibold tabular-nums ${valueColor}`}>{value}</div>
      {sublabel && <div className="mt-1 text-xs text-ink-muted">{sublabel}</div>}
    </div>
  );
}
