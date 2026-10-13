"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { generateAppeal, getAppealsForClaim, updateAppealStatus } from "@/lib/api";
import { formatCurrency, formatDate, formatDateTime } from "@/lib/format";
import type { AppealListItem, AppealLetter } from "@/lib/types";

const STATUS_LABEL: Record<string, string> = { draft: "Draft", reviewed: "Reviewed", sent: "Sent to Payer" };

export default function AppealCard({ item }: { item: AppealListItem }) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const [letter, setLetter] = useState<AppealLetter | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGenerate() {
    setBusy(true);
    setError(null);
    try {
      const newLetter = await generateAppeal(item.claim_id);
      setLetter(newLetter);
      setExpanded(true);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to generate appeal");
    } finally {
      setBusy(false);
    }
  }

  async function toggleExpand() {
    if (expanded) {
      setExpanded(false);
      return;
    }
    setBusy(true);
    try {
      const letters = await getAppealsForClaim(item.claim_id);
      setLetter(letters[0] || null);
      setExpanded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load letter");
    } finally {
      setBusy(false);
    }
  }

  async function advanceStatus(next: string) {
    if (!letter) return;
    setBusy(true);
    try {
      await updateAppealStatus(letter.id, next);
      const letters = await getAppealsForClaim(item.claim_id);
      setLetter(letters[0] || null);
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update status");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-hairline bg-surface p-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="font-semibold text-ink">{item.claim_number} · {item.first_name} {item.last_name}</div>
          <div className="mt-1 text-sm text-ink-secondary">{item.payer_name} · denied {formatDate(item.decided_at)}</div>
          <p className="mt-2 max-w-xl text-sm text-ink-secondary">{item.denial_reason}</p>
        </div>
        <div className="text-right">
          <div className="font-semibold tabular-nums text-ink">{formatCurrency(item.total_billed)}</div>
          {item.appeal_status && (
            <span className="mt-1 inline-block rounded-full bg-brand/10 px-2.5 py-1 text-xs font-semibold text-brand">
              {STATUS_LABEL[item.appeal_status]}
            </span>
          )}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        {!item.appeal_id && (
          <button
            disabled={busy}
            onClick={handleGenerate}
            className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand/90 disabled:opacity-60"
          >
            {busy ? "Drafting..." : "Draft Appeal Letter"}
          </button>
        )}
        {item.appeal_id && (
          <button
            disabled={busy}
            onClick={toggleExpand}
            className="rounded-lg border border-hairline bg-surface px-4 py-2 text-sm font-semibold text-ink hover:bg-surface-muted disabled:opacity-60"
          >
            {expanded ? "Hide Letter" : "View Letter"}
          </button>
        )}
        {expanded && letter && letter.status === "draft" && (
          <button disabled={busy} onClick={() => advanceStatus("reviewed")} className="rounded-lg border border-hairline px-4 py-2 text-sm font-medium text-ink-secondary hover:bg-surface-muted">
            Mark Reviewed
          </button>
        )}
        {expanded && letter && letter.status === "reviewed" && (
          <button disabled={busy} onClick={() => advanceStatus("sent")} className="rounded-lg border border-hairline px-4 py-2 text-sm font-medium text-ink-secondary hover:bg-surface-muted">
            Mark Sent to Payer
          </button>
        )}
      </div>
      {error && <p className="mt-2 text-xs text-risk-high">{error}</p>}

      {expanded && letter && (
        <div className="mt-4 rounded-xl border border-hairline bg-surface-muted p-6 shadow-sm">
          <div className="flex items-center justify-between border-b border-hairline pb-3">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-brand">Official Appeal Document</span>
              <h4 className="text-sm font-semibold text-ink">Reimbursement Appeal Letter — {item.claim_number}</h4>
            </div>
            <button
              onClick={() => {
                const printWindow = window.open("", "_blank");
                if (printWindow) {
                  printWindow.document.write(`
                    <html>
                      <head>
                        <title>Appeal Letter - ${item.claim_number}</title>
                        <style>
                          body { font-family: 'Times New Roman', serif; padding: 40px; line-height: 1.6; color: #111; }
                          h2 { text-align: center; text-transform: uppercase; margin-bottom: 20px; border-bottom: 2px solid #333; padding-bottom: 10px; }
                          .meta { margin-bottom: 30px; font-size: 14px; }
                          .content { white-space: pre-wrap; font-size: 15px; }
                          .footer { margin-top: 50px; font-size: 12px; border-top: 1px solid #ccc; pt: 10px; text-align: center; color: #666; }
                        </style>
                      </head>
                      <body>
                        <h2>Formulary & Reimbursement Appeal Notice</h2>
                        <div class="meta">
                          <strong>Patient Name:</strong> ${item.first_name} ${item.last_name}<br/>
                          <strong>Claim Number:</strong> ${item.claim_number}<br/>
                          <strong>Payer:</strong> ${item.payer_name}<br/>
                          <strong>Billed Amount:</strong> ${formatCurrency(item.total_billed)}<br/>
                        </div>
                        <div class="content">${letter.letter_content}</div>
                        <div class="footer">Generated by CuraSense AI Intelligence Platform · Confidential Healthcare Communication</div>
                      </body>
                    </html>
                  `);
                  printWindow.document.close();
                  printWindow.focus();
                  printWindow.print();
                }
              }}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-brand/90"
            >
              📄 Download / Print PDF
            </button>
          </div>

          <p className="mt-4 whitespace-pre-wrap font-mono text-xs leading-relaxed text-ink-secondary">{letter.letter_content}</p>

          {letter.evidence_used.length > 0 && (
            <div className="mt-4 border-t border-hairline pt-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-ink-muted">Cited Payer Policies</div>
              <ul className="mt-2 flex flex-wrap gap-2">
                {letter.evidence_used.map((e) => (
                  <li key={e.policy_number} className="rounded-md border border-hairline bg-surface px-3 py-1 text-xs text-ink-secondary">
                    <strong className="text-brand">{e.policy_number}:</strong> {e.title}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="mt-4 text-xs text-ink-muted">Generated {formatDateTime(letter.generated_at)} · Review required prior to submission</p>
        </div>
      )}
    </div>
  );
}
