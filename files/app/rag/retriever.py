from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from config.settings import settings


@dataclass
class RetrievedChunk:
    text: str
    score: float
    rerank_score: float
    source: str
    chunk_index: int

_encoder: SentenceTransformer | None = None
_cross_encoder = None
_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def _get_encoder() -> SentenceTransformer:
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer("all-MiniLM-L6-v2")
    return _encoder


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


def search(query: str, top_k: int = 5, source_filter: str | None = None, collection: str | None = None) -> list[dict]:
    try:
        client = _get_client()
        encoder = _get_encoder()

        query_vector = encoder.encode(query).tolist()

        qdrant_filter = None
        if source_filter:
            qdrant_filter = Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=source_filter))]
            )

        col = collection or settings.qdrant_collection
        results = client.search(
            collection_name=col,
            query_vector=query_vector,
            limit=top_k * 2,
            query_filter=qdrant_filter,
        )

        if not results:
            return []

        cross = _get_cross_encoder()
        pairs = [(query, hit.payload.get("text", "")) for hit in results]
        scores = cross.predict(pairs)

        scored = list(zip(results, scores))
        scored.sort(key=lambda x: x[1], reverse=True)

        top = scored[:top_k]
        return [
            {
                "score": round(float(score), 4),
                "text": hit.payload.get("text", ""),
                "source": hit.payload.get("source", "unknown"),
                "metadata": hit.payload.get("metadata", {}),
            }
            for hit, score in top
        ]

    except Exception as exc:
        return []


def retrieve_as_context(query: str, top_k: int = 5, source_filter: str | None = None, collection: str | None = None) -> str:
    docs = search(query, top_k=top_k, source_filter=source_filter, collection=collection)
    if not docs:
        return "[RAG unavailable — no results returned]"

    lines = []
    for i, doc in enumerate(docs, 1):
        lines.append(f"[{i}] (relevance={doc['score']}) {doc['text']}")

    return "\n\n".join(lines)


def retrieve(query: str, top_k: int = 5, rerank: bool = True, collection: str | None = None) -> list[RetrievedChunk]:
    results = search(query, top_k=top_k * 2 if rerank else top_k, collection=collection)
    if not results:
        return []

    if rerank:
        cross = _get_cross_encoder()
        pairs = [(query, doc["text"]) for doc in results]
        scores = cross.predict(pairs)
        scored = list(zip(results, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        results = [doc for doc, _ in scored[:top_k]]

    return [
        RetrievedChunk(
            text=doc["text"],
            score=doc["score"],
            rerank_score=doc["score"],
            source=doc["source"],
            chunk_index=i,
        )
        for i, doc in enumerate(results)
    ]
