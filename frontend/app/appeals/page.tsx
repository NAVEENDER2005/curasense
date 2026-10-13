import { getAppeals } from "@/lib/api";
import AppealCard from "@/components/AppealCard";

export const dynamic = "force-dynamic";

export default async function AppealsPage() {
  const appeals = await getAppeals();

  return (
    <div className="mx-auto max-w-4xl px-8 py-8">
      <h1 className="text-2xl font-semibold text-ink">Appeals Hub</h1>
      <p className="mt-1 text-sm text-ink-secondary">
        Auto-generated, evidence-based medical necessity appeal letters for denied claims.
      </p>

      <div className="mt-6 flex flex-col gap-4">
        {appeals.length === 0 && (
          <div className="rounded-xl border border-dashed border-hairline p-10 text-center text-sm text-ink-muted">
            No denied claims on file.
          </div>
        )}
        {appeals.map((item) => (
          <AppealCard key={item.claim_id} item={item} />
        ))}
      </div>
    </div>
  );
}
