import { getPolicies } from "@/lib/api";
import { formatDate } from "@/lib/format";
import PolicySearch from "@/components/PolicySearch";

export const dynamic = "force-dynamic";

export default async function PoliciesPage() {
  const policies = await getPolicies();
  const byPayer = policies.reduce<Record<string, typeof policies>>((acc, p) => {
    (acc[p.payer_name] ||= []).push(p);
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-4xl px-8 py-8">
      <h1 className="text-2xl font-semibold text-ink">Policy Intelligence</h1>
      <p className="mt-1 text-sm text-ink-secondary">Payer policy documents indexed for real-time claim validation.</p>

      <div className="mt-6">
        <PolicySearch />
      </div>

      <div className="mt-6 flex flex-col gap-6">
        {Object.entries(byPayer).map(([payerName, docs]) => (
          <div key={payerName} className="rounded-xl border border-hairline bg-surface p-5">
            <h2 className="text-sm font-semibold text-ink">{payerName}</h2>
            <div className="mt-3 flex flex-col gap-3">
              {docs.map((doc) => (
                <details key={doc.id} className="rounded-lg border border-hairline p-3">
                  <summary className="cursor-pointer text-sm font-medium text-ink">
                    {doc.policy_number}: {doc.title}
                    {doc.effective_date && <span className="ml-2 text-xs font-normal text-ink-muted">effective {formatDate(doc.effective_date)}</span>}
                  </summary>
                  <p className="mt-2 text-sm text-ink-secondary">{doc.content}</p>
                </details>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
