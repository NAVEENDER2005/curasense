# AI Intelligence Hub

| Module | Feature | Real mode | Offline/mock mode |
|---|---|---|---|
| `extraction.py` | GenAI Document Extraction / Auto-Coding Co-Pilot | rule engine + GPT-4o narrative | rule engine only |
| `rag.py` + `vectorstore.py` | RAG Policy Parser | Pinecone + OpenAI embeddings | local cosine-similarity store + hashed embeddings |
| `scoring.py` + `policy_rules.py` | Predictive Denial Engine | same rule engine (no key needed) | same |
| `explainer.py` | Denial Explainer | rule bullets + Claude summary | rule bullets only |
| `appeals.py` | Automated Appeals Generation | Claude-drafted letter | templated letter |
| `fraud.py` | Anomaly / Fraud Detection | rule engine (no key needed) | same |
| `chat.py` | Ask My Data | Claude, grounded in precomputed aggregates | raw aggregate dump |

## Design choices worth knowing

- **Nothing here requires an API key to run.** `config.py` detects which keys
  are set and every LLM-touching module falls back to a deterministic,
  rule-based/templated path. This means the full ingest → score → explain →
  appeal demo works out of the box; adding `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
  upgrades the prose quality without changing behavior.
- **Denial scoring is a transparent rule engine, not a black-box model**
  (`policy_rules.py`). Every risk point traces to a specific, citable policy
  check. This satisfies the "explainable, auditable" compliance requirement
  directly, rather than bolting an explainer onto an opaque model after the
  fact. Upgrading to a trained ML model later: keep `policy_rules.py`'s output
  as engineered features, add a model that reweights them using accumulated
  real outcomes (claims that were actually denied vs. paid).
- **Ask My Data never generates or runs SQL.** The LLM only answers over
  pre-computed, already-authorized aggregate stats the backend passes in
  (`chat.build_context`). This avoids giving an LLM direct query access to a
  datastore holding PHI-adjacent financial records.
- **Vector store is pluggable** (`vectorstore.py`): local numpy store by
  default, Pinecone if `PINECONE_API_KEY` is set. Same interface either way.

## PHI / compliance flags

Every function that can send clinical note text to a third-party LLM API is
marked with a `COMPLIANCE NOTE` docstring comment (`extraction.py`,
`appeals.py`). In this demo all clinical data is synthetic; in production,
those code paths require a signed BAA with the LLM vendor before real PHI
flows through them.
