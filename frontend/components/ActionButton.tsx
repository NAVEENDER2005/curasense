"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

export default function ActionButton({
  onRun, label, busyLabel, variant = "primary",
}: {
  onRun: () => Promise<unknown>;
  label: string;
  busyLabel: string;
  variant?: "primary" | "secondary";
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const styles = variant === "primary"
    ? "bg-brand text-white hover:bg-brand/90"
    : "border border-hairline bg-surface text-ink hover:bg-surface-muted";

  return (
    <div>
      <button
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError(null);
          try {
            await onRun();
            router.refresh();
          } catch (e) {
            setError(e instanceof Error ? e.message : "Something went wrong");
          } finally {
            setBusy(false);
          }
        }}
        className={`rounded-lg px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${styles}`}
      >
        {busy ? busyLabel : label}
      </button>
      {error && <p className="mt-2 text-xs text-risk-high">{error}</p>}
    </div>
  );
}
