import type { ClaimStatus } from "@/lib/types";

const LABELS: Record<ClaimStatus, string> = {
  draft: "Draft",
  ready: "Ready to Submit",
  submitted: "Submitted",
  paid: "Paid",
  denied: "Denied",
  appealed: "Appealed",
  recovered: "Recovered",
};

const STYLES: Record<ClaimStatus, string> = {
  draft: "bg-surface-muted text-ink-secondary",
  ready: "bg-brand/10 text-brand",
  submitted: "bg-brand/10 text-brand",
  paid: "bg-risk-low/10 text-risk-low",
  denied: "bg-risk-high/10 text-risk-high",
  appealed: "bg-risk-medium/15 text-[#8a5a00]",
  recovered: "bg-risk-low/10 text-risk-low",
};

export default function StatusBadge({ status }: { status: ClaimStatus }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${STYLES[status]}`}>
      {LABELS[status]}
    </span>
  );
}
