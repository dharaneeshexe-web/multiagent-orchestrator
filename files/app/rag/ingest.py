from __future__ import annotations

import hashlib
import os
from typing import Iterator

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from sentence_transformers import SentenceTransformer

from config.settings import settings

_encoder: SentenceTransformer | None = None
_client: QdrantClient | None = None


CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


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


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if not text.strip():
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start += size - overlap
        if start >= len(text):
            break
    return chunks


def _ensure_collection(client: QdrantClient, collection: str, vector_size: int = 384):
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if collection not in names:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )


def ingest_raw(text: str, source: str = "manual", metadata: dict | None = None, collection: str | None = None) -> int:
    client = _get_client()
    encoder = _get_encoder()
    col = collection or settings.qdrant_collection

    test_vec = encoder.encode("init").tolist()
    _ensure_collection(client, col, vector_size=len(test_vec))

    chunks = _chunk_text(text)

    points = []
    for chunk in chunks:
        chunk_id = hashlib.sha256(chunk.encode()).hexdigest()[:32]
        vector = encoder.encode(chunk).tolist()
        points.append(
            PointStruct(
                id=chunk_id,
                vector=vector,
                payload={
                    "text": chunk,
                    "source": source,
                    "metadata": metadata or {},
                },
            )
        )

    if points:
        client.upsert(
            collection_name=col,
            points=points,
        )

    return len(points)


def ingest_file(filepath: str, source: str | None = None, collection: str | None = None) -> int:
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    doc_source = source or os.path.basename(filepath)
    return ingest_raw(text, source=doc_source, metadata={"filepath": filepath}, collection=collection)
