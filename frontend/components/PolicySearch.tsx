"use client";

import { useState } from "react";
import { searchPolicies } from "@/lib/api";
import type { PolicySearchResult } from "@/lib/types";

const PAYERS = [
  { code: "AETNA", name: "Aetna" },
  { code: "UHC", name: "UnitedHealthcare" },
  { code: "MEDICARE", name: "Medicare" },
];

export default function PolicySearch() {
  const [payerCode, setPayerCode] = useState("AETNA");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PolicySearchResult[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (query.trim().length < 2) return;
    setBusy(true);
    setError(null);
    try {
      const r = await searchPolicies(query, payerCode);
      setResults(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-hairline bg-surface p-5">
      <h2 className="text-sm font-semibold text-ink">Policy Intelligence Search</h2>
      <p className="mt-0.5 text-xs text-ink-muted">
        RAG-based search: describe the clinical scenario, get back the specific payer policy language that applies.
      </p>
      <form onSubmit={handleSearch} className="mt-3 flex flex-wrap gap-2">
        <select
          value={payerCode}
          onChange={(e) => setPayerCode(e.target.value)}
          className="rounded-lg border border-hairline bg-surface px-3 py-2 text-sm text-ink"
        >
          {PAYERS.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
        </select>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. lumbar MRI without conservative therapy"
          className="min-w-64 flex-1 rounded-lg border border-hairline bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-muted"
        />
        <button
          disabled={busy}
          className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand/90 disabled:opacity-60"
        >
          {busy ? "Searching..." : "Search"}
        </button>
      </form>
      {error && <p className="mt-2 text-xs text-risk-high">{error}</p>}
      {results && (
        <div className="mt-4 flex flex-col gap-2">
          {results.length === 0 && <p className="text-sm text-ink-muted">No matching policies found.</p>}
          {results.map((r) => (
            <div key={r.id} className="rounded-lg border border-hairline p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-ink">{r.metadata.policy_number}: {r.metadata.title}</span>
                <span className="text-xs text-ink-muted">relevance {r.score.toFixed(2)}</span>
              </div>
              <p className="mt-1 text-xs text-ink-secondary">{r.text.slice(0, 280)}...</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
