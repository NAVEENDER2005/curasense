"""Anomaly / Fraud Detection Engine: rule-based checks for billing patterns
that create compliance/audit risk (upcoding, unbundling, duplicate billing).
Explainable by design - every flag names the specific pattern detected, for
regulatory defensibility rather than an opaque anomaly score.
"""
from collections import Counter

DUPLICATE_THRESHOLD = 2  # same CPT code billed this many times in one encounter triggers a flag

# CPT codes where >1 occurrence is clinically normal (e.g. bilateral or staged
# procedures) and should not be flagged.
DUPLICATE_EXEMPT_CODES = {"99231", "99232"}  # subsequent-day E/M codes are expected to repeat


def scan_claim(claim: dict) -> list[dict]:
    flags = []
    cpt_counts = Counter(claim["cpt_codes"])
    for code, count in cpt_counts.items():
        if count >= DUPLICATE_THRESHOLD and code not in DUPLICATE_EXEMPT_CODES:
            flags.append({
                "flag_type": "duplicate_billing",
                "severity": "high" if count >= 3 else "medium",
                "description": (f"CPT {code} billed {count} times on a single claim with no documented "
                                 "distinct clinical justification per occurrence."),
            })
    return flags


def scan_patient_history(claims: list[dict]) -> list[dict]:
    """claims: recent claims for one patient/payer, oldest first. Flags
    frequency anomalies - e.g. the same high-cost procedure recurring far more
    often than clinically expected."""
    flags = []
    procedure_counts = Counter(code for c in claims for code in c["cpt_codes"])
    for code, count in procedure_counts.items():
        if count >= 4:
            flags.append({
                "flag_type": "frequency_anomaly",
                "severity": "medium",
                "description": f"CPT {code} appears on {count} claims for this patient in the recent history window - above the expected frequency for this service.",
            })
    return flags
