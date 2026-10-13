import Link from "next/link";
import { notFound } from "next/navigation";
import { getClaimDetail } from "@/lib/api";
import { formatCurrency, formatDateTime } from "@/lib/format";
import RiskBadge from "@/components/RiskBadge";
import StatusBadge from "@/components/StatusBadge";
import ScoreClaimAction from "@/components/ScoreClaimAction";
import SubmitClaimAction from "@/components/SubmitClaimAction";
import FormattedBullet from "@/components/FormattedBullet";

export const dynamic = "force-dynamic";

const SEVERITY_STYLE: Record<string, string> = {
  high: "border-l-4 border-risk-high bg-risk-high/5",
  medium: "border-l-4 border-risk-medium bg-risk-medium/10",
  low: "border-l-4 border-risk-low bg-risk-low/5",
  info: "border-l-4 border-hairline bg-surface-muted",
};

export default async function ClaimDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let detail;
  try {
    detail = await getClaimDetail(id);
  } catch {
    notFound();
  }
  const { claim, notes, latest_score, latest_extraction, fraud_flags, appeal } = detail;
  const note = notes[0];

  return (
    <div className="mx-auto max-w-6xl px-8 py-8">
      <Link href="/claims" className="text-sm text-ink-secondary hover:text-brand">← Back to Provider Workflow</Link>

      <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-ink">{claim.claim_number}</h1>
            <StatusBadge status={claim.status} />
          </div>
          <p className="mt-1 text-sm text-ink-secondary">
            {claim.first_name} {claim.last_name} (MRN {claim.mrn}) · {claim.payer_name}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-xs text-ink-muted">Total Billed</div>
            <div className="text-xl font-semibold tabular-nums text-ink">{formatCurrency(claim.total_billed)}</div>
          </div>
          <RiskBadge level={latest_score?.risk_level ?? null} score={latest_score?.risk_score} />
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <ScoreClaimAction claimId={claim.id} hasScore={!!latest_score} />
        {claim.status === "ready" && <SubmitClaimAction claimId={claim.id} />}
        {claim.status === "denied" && (
          <Link
            href="/appeals"
            className="rounded-lg border border-hairline bg-surface px-4 py-2 text-sm font-semibold text-ink hover:bg-surface-muted"
          >
            {appeal ? "View Appeal in Appeals Hub →" : "Draft Appeal in Appeals Hub →"}
          </Link>
        )}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* LEFT: original claim file */}
        <section className="rounded-xl border border-hairline bg-surface p-5">
          <h2 className="text-sm font-semibold text-ink">Claim File</h2>

          <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div><dt className="text-ink-muted">Encounter</dt><dd className="text-ink">{claim.encounter_type}{claim.department ? ` · ${claim.department}` : ""}</dd></div>
            <div><dt className="text-ink-muted">Attending</dt><dd className="text-ink">{claim.attending_physician || "-"}</dd></div>
            <div><dt className="text-ink-muted">Diagnosis (ICD-10)</dt><dd className="font-mono text-ink">{claim.icd10_codes.join(", ")}</dd></div>
            <div><dt className="text-ink-muted">Procedure (CPT)</dt><dd className="font-mono text-ink">{claim.cpt_codes.join(", ")}</dd></div>
            {claim.denial_reason && (
              <div className="col-span-2">
                <dt className="text-ink-muted">Denial Reason (payer-stated)</dt>
                <dd className="text-risk-high">{claim.denial_reason}</dd>
              </div>
            )}
          </dl>

          {note && (
            <div className="mt-5">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">
                {note.note_type.replace("_", " ")} {note.author ? `· ${note.author}` : ""}
              </h3>
              <p className="mt-2 whitespace-pre-wrap rounded-lg bg-surface-muted p-4 text-sm leading-relaxed text-ink-secondary">
                {note.content}
              </p>
            </div>
          )}
        </section>

        {/* RIGHT: AI-suggested modifications and evidence */}
        <section className="rounded-xl border border-hairline bg-surface p-5">
          <h2 className="text-sm font-semibold text-ink">AI Intelligence</h2>

          {!latest_score && (
            <p className="mt-3 text-sm text-ink-muted">
              This claim hasn&apos;t been analyzed yet. Run AI Analysis to get a denial-risk score, policy
              validation, coding suggestions, and compliance checks.
            </p>
          )}

          {latest_score && (
            <div className="mt-4">
              {latest_score.reasons.executive_summary && !latest_score.reasons.executive_summary.includes("[mock-llm-response]") && (
                <p className="rounded-lg bg-brand/5 p-3 text-sm text-ink-secondary">{latest_score.reasons.executive_summary}</p>
              )}
              <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide text-ink-muted">Denial Explainer</h3>
              <div className="mt-2 flex flex-col gap-2">
                {latest_score.reasons.bullets.map((bullet, i) => {
                  const isPositive = bullet.startsWith("✓");
                  return (
                    <FormattedBullet
                      key={i}
                      text={bullet}
                      className={`rounded-md p-3 text-sm text-ink-secondary ${isPositive ? SEVERITY_STYLE.low : SEVERITY_STYLE[latest_score.reasons.raw_reasons[i]?.severity] || SEVERITY_STYLE.info}`}
                    />
                  );
                })}
              </div>
              <p className="mt-3 text-xs text-ink-muted">Model: {latest_score.model_version} · scored {formatDateTime(latest_score.scored_at)}</p>
            </div>
          )}

          {latest_extraction && latest_extraction.missing_charges.length > 0 && (
            <div className="mt-5">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Auto-Coding Co-Pilot: Suggested Additions</h3>
              <div className="mt-2 flex flex-col gap-2">
                {latest_extraction.missing_charges.map((m, i) => (
                  <div key={i} className="rounded-md border border-hairline p-3 text-sm">
                    <span className="font-mono font-semibold text-brand">{m.code_system} {m.code}</span>
                    <span className="text-ink-secondary"> — {m.description}</span>
                    <p className="mt-1 text-xs text-ink-muted">{m.rationale}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {fraud_flags.length > 0 && (
            <div className="mt-5">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Compliance / Fraud Flags</h3>
              <div className="mt-2 flex flex-col gap-2">
                {fraud_flags.map((f, i) => (
                  <div key={i} className="rounded-md border border-risk-high/30 bg-risk-high/5 p-3 text-sm text-ink-secondary">
                    <span className="font-semibold text-risk-high">{f.flag_type.replace("_", " ")}</span>: {f.description}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
