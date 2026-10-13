import type { RiskLevel } from "@/lib/types";

const STYLES: Record<RiskLevel, { bg: string; text: string; label: string; icon: string }> = {
  high: { bg: "bg-risk-high/10", text: "text-risk-high", label: "High Risk", icon: "●" },
  medium: { bg: "bg-risk-medium/15", text: "text-[#8a5a00]", label: "Medium Risk", icon: "●" },
  low: { bg: "bg-risk-low/10", text: "text-risk-low", label: "Low Risk", icon: "●" },
};

export default function RiskBadge({ level, score }: { level: RiskLevel | null; score?: string | number | null }) {
  if (!level) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-muted px-2.5 py-1 text-xs font-medium text-ink-muted">
        Not yet scored
      </span>
    );
  }
  const s = STYLES[level];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full ${s.bg} ${s.text} px-2.5 py-1 text-xs font-semibold`}>
      <span aria-hidden>{s.icon}</span>
      {s.label}
      {score !== undefined && score !== null && <span className="font-normal opacity-80">({Math.round(Number(score))})</span>}
    </span>
  );
}
