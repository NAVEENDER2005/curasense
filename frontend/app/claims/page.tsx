import Link from "next/link";
import { getClaims } from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import RiskBadge from "@/components/RiskBadge";
import StatusBadge from "@/components/StatusBadge";
import type { ClaimListItem } from "@/lib/types";

export const dynamic = "force-dynamic";

const ACTIONABLE_STATUSES = new Set(["ready", "submitted"]);

function ClaimRow({ claim }: { claim: ClaimListItem }) {
  return (
    <Link
      href={`/claims/${claim.id}`}
      className="flex items-center justify-between gap-4 rounded-lg border border-hairline bg-surface px-5 py-4 transition-colors hover:border-brand/40 hover:bg-brand/5"
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-ink">{claim.claim_number}</span>
          <StatusBadge status={claim.status} />
        </div>
        <div className="mt-1 truncate text-sm text-ink-secondary">
          {claim.first_name} {claim.last_name} · {claim.payer_name} · {claim.encounter_type}
          {claim.department ? ` · ${claim.department}` : ""}
        </div>
      </div>
      <div className="shrink-0 text-right">
        <div className="font-semibold tabular-nums text-ink">{formatCurrency(claim.total_billed)}</div>
        <div className="mt-1"><RiskBadge level={claim.risk_level} score={claim.risk_score} /></div>
      </div>
    </Link>
  );
}

export default async function ClaimsPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string }>;
}) {
  const { view } = await searchParams;
  const showAll = view === "all";

  const allClaims = await getClaims();
  const actionable = allClaims.filter((c) => ACTIONABLE_STATUSES.has(c.status) && c.risk_level === "high");
  const visible = showAll ? allClaims : actionable;

  return (
    <div className="mx-auto max-w-4xl px-8 py-8">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Provider Workflow</h1>
          <p className="mt-1 text-sm text-ink-secondary">
            {showAll
              ? "All claims in the system."
              : "High-risk claims that need attention before submission - everything else is intentionally hidden."}
          </p>
        </div>
        <div className="flex shrink-0 gap-2 rounded-lg bg-surface-muted p-1 text-sm">
          <Link
            href="/claims"
            className={`rounded-md px-3 py-1.5 font-medium ${!showAll ? "bg-surface text-ink shadow-sm" : "text-ink-secondary"}`}
          >
            High Risk Only
          </Link>
          <Link
            href="/claims?view=all"
            className={`rounded-md px-3 py-1.5 font-medium ${showAll ? "bg-surface text-ink shadow-sm" : "text-ink-secondary"}`}
          >
            All Claims ({allClaims.length})
          </Link>
        </div>
      </div>

      <div className="mt-6 flex flex-col gap-3">
        {visible.length === 0 && (
          <div className="rounded-xl border border-dashed border-hairline p-10 text-center text-sm text-ink-muted">
            {showAll ? "No claims found." : "Nothing needs attention right now - no high-risk pending claims."}
          </div>
        )}
        {visible.map((claim) => (
          <ClaimRow key={claim.id} claim={claim} />
        ))}
      </div>
    </div>
  );
}
