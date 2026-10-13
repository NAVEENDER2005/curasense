"""Automated Appeals Generation: drafts an evidence-based medical necessity
appeal letter for a denied claim, citing the specific clinical documentation
and payer policy language that support reversing the denial.

COMPLIANCE NOTE: note_text (clinical documentation) is included in the prompt
sent to the reasoning LLM when ANTHROPIC_API_KEY is configured - requires a
signed BAA in production before real PHI is sent. The template fallback below
never leaves the process, so appeals can still be drafted with zero LLM calls.
"""
from ai import config
from ai.llm import complete_reasoning
from ai.policy_rules import evaluate_policies
from ai.rag import retrieve_relevant_policies


def _template_letter(claim: dict, patient_name: str, note_text: str, denial_reason: str,
                      supporting_policies: list[dict]) -> str:
    citations = "\n".join(
        f"  - {p['metadata']['policy_number']} ({p['metadata']['title']})" for p in supporting_policies
    )
    return f"""RE: Appeal of Denied Claim {claim['claim_number']}
Patient: {patient_name}
Diagnosis code(s): {', '.join(claim['icd10_codes'])}
Procedure code(s): {', '.join(claim['cpt_codes'])}

To the Claims Review Department:

We are writing to formally appeal the denial of the above-referenced claim.
The stated reason for denial was:

  "{denial_reason}"

The attached clinical documentation supports medical necessity for the
services rendered:

  {note_text.strip()}

This is further supported by the following payer policy provisions:
{citations if citations else '  (no directly matching policy provisions were retrieved for this denial reason)'}

We respectfully request that this claim be reprocessed for payment based on
the clinical evidence above. Please contact our billing office with any
questions or requests for additional documentation.

Sincerely,
CuraSense Revenue Cycle Management Team
(auto-drafted - review required before submission)
"""


def draft_appeal(claim: dict, patient_name: str, note_text: str, denial_reason: str, payer_code: str) -> dict:
    retrieved = retrieve_relevant_policies(
        query_text=f"{denial_reason} {' '.join(claim['icd10_codes'])} {' '.join(claim['cpt_codes'])}",
        payer_code=payer_code, top_k=4,
    )
    # Only cite policies this claim actually has a codified, applicable check
    # for (same rule engine scoring.py uses) - otherwise a claim can end up
    # citing an unrelated policy just because it was retrieved for the same
    # payer, which would look like a mistake in a real appeal letter.
    checked = evaluate_policies(claim, note_text, retrieved)
    applicable_numbers = {c["policy_number"] for c in checked if c["passed"] is not None}
    supporting_policies = [p for p in retrieved if p["metadata"]["policy_number"] in applicable_numbers] or retrieved[:1]

    letter = None
    if config.HAS_ANTHROPIC:
        policy_context = "\n".join(f"{p['metadata']['policy_number']}: {p['text']}" for p in supporting_policies)
        letter = complete_reasoning(
            system=("You are a hospital revenue cycle specialist drafting a formal payer appeal letter. "
                     "Cite the provided policy language explicitly. Be factual and only use the clinical "
                     "documentation given - never invent clinical facts. Output the letter only, no preamble."),
            user=(f"Claim: {claim['claim_number']}, patient: {patient_name}\n"
                  f"Denial reason: {denial_reason}\n\nClinical documentation:\n{note_text}\n\n"
                  f"Relevant payer policy provisions:\n{policy_context}"),
        )

    if not letter or letter.startswith("[mock-llm-response]"):
        letter = _template_letter(claim, patient_name, note_text, denial_reason, supporting_policies)

    return {
        "letter_content": letter,
        "evidence_used": [
            {"policy_number": p["metadata"]["policy_number"], "title": p["metadata"]["title"]}
            for p in supporting_policies
        ],
        "model_used": "claude-sonnet-5" if config.HAS_ANTHROPIC else "template-v1",
    }
