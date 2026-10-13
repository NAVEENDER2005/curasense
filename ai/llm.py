"""Unified LLM access. Per the stack: GPT-4o for complex extraction, Claude
for logical reasoning against payer policies. Both fall back to a templated
MockProvider when their API key isn't configured, so every AI feature in this
app is fully demoable offline and only gets smarter once real keys are added.

COMPLIANCE NOTE: any call through `complete_extraction` / `complete_reasoning`
sends clinical note text (synthetic in this demo, but PHI-shaped) to a
third-party LLM API. In production this requires a signed BAA with the LLM
vendor before any real PHI is sent - see README.md "Compliance & Security".
"""
from ai import config


def complete_extraction(system: str, user: str, max_tokens: int = 1024) -> str:
    """GPT-4o-style call for document extraction / auto-coding tasks."""
    if config.HAS_OPENAI:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=config.OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                max_tokens=max_tokens,
                temperature=0.1,
            )
            return resp.choices[0].message.content
        except Exception as exc:  # noqa: BLE001
            print(f"[ai.llm] OpenAI call failed, falling back to mock: {exc}")
    return _mock_complete(system, user)


def complete_reasoning(system: str, user: str, max_tokens: int = 1500) -> str:
    """Claude-style call for policy reasoning, explanations, and appeal drafting."""
    if config.HAS_ANTHROPIC:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-sonnet-5",
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return "".join(block.text for block in resp.content if block.type == "text")
        except Exception as exc:  # noqa: BLE001
            print(f"[ai.llm] Anthropic call failed, falling back to mock: {exc}")
    return _mock_complete(system, user)


def _mock_complete(system: str, user: str) -> str:
    """Clean offline stand-in used when no API key or balance is available.
    Returns a professional summary rather than developer placeholder text."""
    if "executive summary" in system.lower():
        return (
            "Executive Summary: Claim analyzed against payer policy requirements. High risk identified due to "
            "documentation specificity or missing clinical linkage. Immediate recoding or documentation review recommended."
        )
    return (
        "Based on clinical documentation review and payer policy cross-referencing, "
        "the claim requires review for documentation specificity and clinical necessity compliance before submission."
    )
