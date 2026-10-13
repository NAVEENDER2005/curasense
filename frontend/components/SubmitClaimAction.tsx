"use client";

import ActionButton from "@/components/ActionButton";
import { submitClaim } from "@/lib/api";

export default function SubmitClaimAction({ claimId }: { claimId: string }) {
  return (
    <ActionButton
      variant="secondary"
      label="Submit Claim"
      busyLabel="Submitting..."
      onRun={() => submitClaim(claimId)}
    />
  );
}
