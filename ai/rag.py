"""RAG policy parser: indexes payer policy documents and retrieves the ones
relevant to a given claim, for real-time policy validation and appeal
evidence citation.
"""
from ai.vectorstore import get_vector_store


def index_policies(policies: list[dict]) -> int:
    """policies: rows shaped like {id, payer_code, policy_number, title,
    category, content}. Returns number of documents indexed."""
    store = get_vector_store()
    ids = [p["id"] for p in policies]
    texts = [f"{p['title']}\n{p['content']}" for p in policies]
    metadatas = [
        {
            "payer_code": p["payer_code"],
            "policy_number": p["policy_number"],
            "title": p["title"],
            "category": p.get("category"),
        }
        for p in policies
    ]
    store.upsert(ids, texts, metadatas)
    return len(ids)


def retrieve_relevant_policies(query_text: str, payer_code: str, top_k: int = 4) -> list[dict]:
    """Returns the top_k policies (for this payer) most relevant to query_text,
    each with a similarity score and full metadata for citation."""
    store = get_vector_store()
    return store.query(
        query_text=query_text,
        top_k=top_k,
        filter_fn=lambda meta: meta.get("payer_code") == payer_code,
    )
