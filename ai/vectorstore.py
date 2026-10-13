"""Vector storage abstraction for payer policy documents.

Default: LocalVectorStore, a small numpy-backed cosine-similarity index
persisted to ai/.vector_cache/. Zero external services required.

If PINECONE_API_KEY is set, PineconeVectorStore is used instead, matching the
stack in the pitch deck. Both implement the same tiny interface so the RAG
layer (ai/rag.py) doesn't care which is active.
"""
import json
import pathlib
from typing import Protocol

import numpy as np

from ai import config
from ai.embeddings import cosine_similarity, embed


class VectorStore(Protocol):
    def upsert(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None: ...
    def query(self, query_text: str, top_k: int, filter_fn=None) -> list[dict]: ...


class LocalVectorStore:
    """Cosine-similarity search over an in-memory list, persisted as JSON."""

    def __init__(self, namespace: str = "policies"):
        self._path = config.VECTOR_CACHE_DIR / f"{namespace}.json"
        self._items: list[dict] = []
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            for item in raw:
                item["vector"] = np.array(item["vector"], dtype=np.float32)
            self._items = raw

    def _save(self):
        serializable = [
            {**{k: v for k, v in item.items() if k != "vector"}, "vector": item["vector"].tolist()}
            for item in self._items
        ]
        self._path.write_text(json.dumps(serializable), encoding="utf-8")

    def upsert(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        vectors = embed(texts)
        by_id = {item["id"]: item for item in self._items}
        for _id, text, meta, vec in zip(ids, texts, metadatas, vectors):
            by_id[_id] = {"id": _id, "text": text, "metadata": meta, "vector": vec}
        self._items = list(by_id.values())
        self._save()

    def query(self, query_text: str, top_k: int = 5, filter_fn=None) -> list[dict]:
        if not self._items:
            return []
        [q_vec] = embed([query_text])
        candidates = [i for i in self._items if filter_fn is None or filter_fn(i["metadata"])]
        scored = [
            {"id": i["id"], "text": i["text"], "metadata": i["metadata"],
             "score": cosine_similarity(q_vec, i["vector"])}
            for i in candidates
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


class PineconeVectorStore:
    """Thin wrapper around the Pinecone client. Embeddings still come from
    ai.embeddings.embed (OpenAI if configured, else the offline hash embedder) -
    Pinecone only stores/searches the resulting vectors."""

    def __init__(self, namespace: str = "policies"):
        from pinecone import Pinecone

        pc = Pinecone(api_key=config.PINECONE_API_KEY)
        existing = {idx["name"] for idx in pc.list_indexes()}
        if config.PINECONE_INDEX_NAME not in existing:
            from pinecone import ServerlessSpec

            pc.create_index(
                name=config.PINECONE_INDEX_NAME,
                dimension=256,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        self._index = pc.Index(config.PINECONE_INDEX_NAME)
        self._namespace = namespace

    def upsert(self, ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
        vectors = embed(texts)
        payload = [
            {"id": _id, "values": vec.tolist(), "metadata": {**meta, "text": text}}
            for _id, text, meta, vec in zip(ids, texts, metadatas, vectors)
        ]
        self._index.upsert(vectors=payload, namespace=self._namespace)

    def query(self, query_text: str, top_k: int = 5, filter_fn=None) -> list[dict]:
        [q_vec] = embed([query_text])
        result = self._index.query(
            vector=q_vec.tolist(), top_k=top_k, namespace=self._namespace,
            include_metadata=True,
        )
        matches = [
            {"id": m["id"], "text": m["metadata"].get("text", ""),
             "metadata": {k: v for k, v in m["metadata"].items() if k != "text"},
             "score": m["score"]}
            for m in result["matches"]
        ]
        if filter_fn:
            matches = [m for m in matches if filter_fn(m["metadata"])]
        return matches


_store_singleton: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store_singleton
    if _store_singleton is None:
        if config.HAS_PINECONE:
            try:
                _store_singleton = PineconeVectorStore()
            except Exception as exc:  # noqa: BLE001
                print(f"[ai.vectorstore] Pinecone init failed, falling back to local store: {exc}")
                _store_singleton = LocalVectorStore()
        else:
            _store_singleton = LocalVectorStore()
    return _store_singleton
