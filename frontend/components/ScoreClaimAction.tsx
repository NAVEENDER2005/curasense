"use client";

import ActionButton from "@/components/ActionButton";
import { scoreClaim } from "@/lib/api";

export default function ScoreClaimAction({ claimId, hasScore }: { claimId: string; hasScore: boolean }) {
  return (
    <ActionButton
      variant={hasScore ? "secondary" : "primary"}
      label={hasScore ? "Re-run AI Analysis" : "Run AI Analysis"}
      busyLabel="Analyzing..."
      onRun={() => scoreClaim(claimId)}
    />
  );
}
