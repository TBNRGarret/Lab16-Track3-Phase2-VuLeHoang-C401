"""Semantic memory: Chroma vector store with OpenAI embeddings.

Use for FAQ chunks, docs, domain knowledge. Small persistent collection.
Gracefully degrades to keyword fallback if embeddings are unavailable.
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings


_WORD_RE = re.compile(r"[a-zA-Z0-9_\u00C0-\u1EF9]+", re.UNICODE)


def _keyword_score(query: str, doc: str) -> float:
    q = {w.lower() for w in _WORD_RE.findall(query)}
    d = {w.lower() for w in _WORD_RE.findall(doc)}
    if not q or not d:
        return 0.0
    return len(q & d) / (len(q | d) ** 0.5)


@dataclass
class SemanticMemory:
    collection_name: str = "lab17_semantic"
    persist_dir: str = "data/chroma"
    embedding_model: str = "text-embedding-3-small"
    _client: Any = field(default=None, init=False, repr=False)
    _collection: Any = field(default=None, init=False, repr=False)
    _embed_fn: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        # Try to wire an OpenAI embedding function; fall back to default
        # (all-MiniLM-L6-v2 via onnx) if key is missing — interface stays identical.
        try:
            from chromadb.utils import embedding_functions

            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._embed_fn = embedding_functions.OpenAIEmbeddingFunction(
                    api_key=api_key,
                    model_name=self.embedding_model,
                )
            else:
                self._embed_fn = embedding_functions.DefaultEmbeddingFunction()
        except Exception:
            self._embed_fn = None

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    # ---------- write ----------
    def add(self, text: str, metadata: dict | None = None, doc_id: str | None = None) -> str:
        doc_id = doc_id or str(uuid.uuid4())
        self._collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {"source": "user"}],
        )
        return doc_id

    def add_many(self, texts: list[str], metadatas: list[dict] | None = None) -> list[str]:
        ids = [str(uuid.uuid4()) for _ in texts]
        self._collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas or [{"source": "seed"}] * len(texts),
        )
        return ids

    # ---------- read ----------
    def search(self, query: str, k: int = 3) -> list[dict]:
        """Return [{id, text, metadata, distance}] top-k."""
        try:
            res = self._collection.query(query_texts=[query], n_results=k)
            ids = res.get("ids", [[]])[0]
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            dists = res.get("distances", [[None] * len(ids)])[0]
            return [
                {"id": i, "text": d, "metadata": m or {}, "distance": dist}
                for i, d, m, dist in zip(ids, docs, metas, dists)
            ]
        except Exception:
            # fall back to keyword scan
            all_docs = self._collection.get()
            docs = all_docs.get("documents", [])
            ids = all_docs.get("ids", [])
            metas = all_docs.get("metadatas", [])
            scored = [
                (_keyword_score(query, d), i, d, m)
                for i, d, m in zip(ids, docs, metas)
            ]
            scored.sort(reverse=True)
            return [
                {"id": i, "text": d, "metadata": m or {}, "distance": 1.0 - s}
                for s, i, d, m in scored[:k]
                if s > 0
            ]

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:
            pass
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def as_text(self, hits: list[dict]) -> str:
        if not hits:
            return "(no semantic hits)"
        lines = []
        for h in hits:
            src = h["metadata"].get("source", "?")
            lines.append(f"- ({src}) {h['text']}")
        return "\n".join(lines)
