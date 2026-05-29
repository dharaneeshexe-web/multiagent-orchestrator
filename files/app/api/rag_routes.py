"""
api/rag_routes.py — REST endpoints for the RAG pipeline.

POST /rag/ingest/text      — ingest raw text
POST /rag/ingest/url       — ingest web page text (fetch + chunk + embed)
GET  /rag/search           — search/retrieve chunks for a query
GET  /rag/collections      — list Qdrant collections + vector counts
DELETE /rag/collection     — drop a collection
"""

from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from qdrant_client import QdrantClient
from config.settings import settings
from rag.ingest import ingest_raw
from rag.retriever import retrieve

router = APIRouter(prefix="/rag", tags=["rag"])


# ── Models ────────────────────────────────────────────────────────────────────

class IngestTextRequest(BaseModel):
    text: str
    source: str = "manual"
    collection: str | None = None


class IngestUrlRequest(BaseModel):
    url: str
    collection: str | None = None


class IngestResponse(BaseModel):
    vectors_added: int
    collection: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    rerank: bool = True
    collection: str | None = None


class ChunkResult(BaseModel):
    text: str
    score: float
    rerank_score: float
    source: str
    chunk_index: int


class SearchResponse(BaseModel):
    query: str
    results: list[ChunkResult]
    total: int


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/ingest/text", response_model=IngestResponse)
async def ingest_text(req: IngestTextRequest):
    """Ingest raw text — chunks, embeds, upserts to Qdrant."""
    try:
        col = req.collection or settings.qdrant_collection
        n = ingest_raw(req.text, source=req.source, collection=col)
        return IngestResponse(vectors_added=n, collection=col)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/ingest/url", response_model=IngestResponse)
async def ingest_url(req: IngestUrlRequest):
    """Fetch a URL, strip HTML tags, ingest the text content."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(req.url, follow_redirects=True)
            resp.raise_for_status()
            raw_text = resp.text

        # Naive HTML tag strip — good enough for ingestion
        import re
        text = re.sub(r"<[^>]+>", " ", raw_text)
        text = re.sub(r"\s+", " ", text).strip()

        col = req.collection or settings.qdrant_collection
        n = ingest_raw(text, source=req.url, collection=col)
        return IngestResponse(vectors_added=n, collection=col)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"Fetch failed: {str(exc)}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/search", response_model=SearchResponse)
async def search_rag(query: str, top_k: int = 5, rerank: bool = True, collection: str | None = None):
    """Retrieve + rerank chunks for a query."""
    try:
        chunks = retrieve(query, top_k=top_k, rerank=rerank, collection=collection)
        return SearchResponse(
            query=query,
            results=[
                ChunkResult(
                    text=c.text,
                    score=c.score,
                    rerank_score=c.rerank_score,
                    source=c.source,
                    chunk_index=c.chunk_index,
                )
                for c in chunks
            ],
            total=len(chunks),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/collections")
async def list_collections():
    """List all Qdrant collections with vector count."""
    try:
        client = QdrantClient(url=settings.qdrant_url)
        cols = client.get_collections().collections
        result = []
        for c in cols:
            info = client.get_collection(c.name)
            result.append({
                "name": c.name,
                "vectors_count": info.vectors_count,
                "status": str(info.status),
            })
        return {"collections": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/collection")
async def delete_collection(name: str):
    """Drop a Qdrant collection."""
    try:
        client = QdrantClient(url=settings.qdrant_url)
        client.delete_collection(name)
        return {"deleted": name}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
