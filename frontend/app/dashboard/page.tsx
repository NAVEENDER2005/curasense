import { getDashboardSummary } from "@/lib/api";
import { formatCurrency, formatDate, formatPercent } from "@/lib/format";
import KpiCard from "@/components/KpiCard";
import BarList from "@/components/BarList";
import Link from "next/link";

export const dynamic = "force-dynamic";

const RISK_COLOR: Record<string, string> = {
  high: "var(--color-risk-high)",
  medium: "var(--color-risk-medium)",
  low: "var(--color-risk-low)",
};
const RISK_LABEL: Record<string, string> = { high: "High", medium: "Medium", low: "Low" };

export default async function DashboardPage() {
  const summary = await getDashboardSummary();
  const { kpis } = summary;

  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <h1 className="text-2xl font-semibold text-ink">Revenue Command Center</h1>
      <p className="mt-1 text-sm text-ink-secondary">
        Daily revenue-at-risk, denial trends, and automated recovery statistics.
      </p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Total Billed" value={formatCurrency(kpis.total_billed)} sublabel="All claims in system" />
        <KpiCard
          label="Revenue at Risk"
          value={formatCurrency(kpis.revenue_at_risk)}
          sublabel="High-risk claims not yet paid"
          tone="risk"
        />
        <KpiCard label="Denial Rate" value={formatPercent(kpis.denial_rate)} sublabel={`${kpis.denied_count} of ${kpis.decided_count} decided claims`} tone="risk" />
        <KpiCard label="Claims Pending Review" value={String(kpis.ready_count)} sublabel="Not yet submitted" />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div className="rounded-xl border border-hairline bg-surface p-5">
          <h2 className="text-sm font-semibold text-ink">Pending Claims by Risk Level</h2>
          <p className="mt-0.5 text-xs text-ink-muted">Ready / submitted claims, by predicted denial risk</p>
          <div className="mt-4">
            <BarList
              emptyLabel="No pending claims have been scored yet."
              items={["high", "medium", "low"]
                .map((level) => {
                  const row = summary.risk_distribution.find((r) => r.risk_level === level);
                  return { label: RISK_LABEL[level], value: row?.claim_count || 0, displayValue: String(row?.claim_count || 0), color: RISK_COLOR[level] };
                })
                .filter((i) => i.value > 0)}
            />
          </div>
        </div>

        <div className="rounded-xl border border-hairline bg-surface p-5">
          <h2 className="text-sm font-semibold text-ink">Denied Revenue by Payer</h2>
          <p className="mt-0.5 text-xs text-ink-muted">Total billed amount currently denied, by payer</p>
          <div className="mt-4">
            <BarList
              emptyLabel="No denied claims on file."
              items={summary.denials_by_payer.map((d) => ({
                label: d.payer_name,
                value: parseFloat(d.denied_amount),
                displayValue: formatCurrency(d.denied_amount),
              }))}
            />
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-hairline bg-surface p-5">
        <h2 className="text-sm font-semibold text-ink">Recent Denials</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs text-ink-muted">
                <th className="pb-2 font-medium">Claim</th>
                <th className="pb-2 font-medium">Payer</th>
                <th className="pb-2 font-medium">Amount</th>
                <th className="pb-2 font-medium">Denial Reason</th>
                <th className="pb-2 font-medium">Decided</th>
              </tr>
            </thead>
            <tbody>
              {summary.recent_denials.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-ink-muted">No denied claims yet.</td>
                </tr>
              )}
              {summary.recent_denials.map((d) => (
                <tr key={d.claim_number} className="border-t border-hairline">
                  <td className="py-2.5 font-medium text-ink">
                    <Link href="/appeals" className="hover:text-brand hover:underline">{d.claim_number}</Link>
                  </td>
                  <td className="py-2.5 text-ink-secondary">{d.payer_name}</td>
                  <td className="py-2.5 tabular-nums text-ink-secondary">{formatCurrency(d.total_billed)}</td>
                  <td className="max-w-md truncate py-2.5 text-ink-secondary" title={d.denial_reason}>{d.denial_reason}</td>
                  <td className="py-2.5 text-ink-secondary">{formatDate(d.decided_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
