"""Text -> vector embeddings, with a dependency-free offline fallback.

Real mode (OPENAI_API_KEY set): OpenAI `text-embedding-3-small`.
Offline mode: a feature-hashing bag-of-words vector (numpy + hashlib only).
It's not semantically as strong as a trained embedding model, but it clusters
documents that share clinical/policy vocabulary well enough for this demo's
small policy corpus, and needs no network access or API key.
"""
import hashlib
import re

import numpy as np

from ai import config

EMBED_DIM = 256
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _hash_embed(text: str) -> np.ndarray:
    vec = np.zeros(EMBED_DIM, dtype=np.float32)
    tokens = _TOKEN_RE.findall(text.lower())
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        idx = h % EMBED_DIM
        sign = 1.0 if (h // EMBED_DIM) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def _openai_embed(texts: list[str]) -> list[np.ndarray]:
    from openai import OpenAI

    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [np.array(d.embedding, dtype=np.float32) for d in resp.data]


def embed(texts: list[str]) -> list[np.ndarray]:
    """Embed a batch of texts. Falls back to the offline hashing embedder on
    any error (missing key, network failure, rate limit) so the pipeline never
    hard-fails for lack of a live API."""
    if config.HAS_OPENAI:
        try:
            return _openai_embed(texts)
        except Exception as exc:  # noqa: BLE001 - deliberate graceful degrade
            print(f"[ai.embeddings] OpenAI embedding failed, falling back to offline mode: {exc}")
    return [_hash_embed(t) for t in texts]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0
