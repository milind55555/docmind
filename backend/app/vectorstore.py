"""Vector store wrapper: FAISS (default, on disk) or pgvector (Postgres)."""
from __future__ import annotations

import threading

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from .config import Settings

_COLLECTION = "docmind"


class VectorStore:
    def __init__(self, settings: Settings, embeddings: Embeddings):
        self.s = settings
        self.emb = embeddings
        self._lock = threading.Lock()
        self._faiss = None
        if settings.vector_store == "pgvector":
            from langchain_postgres import PGVector

            self._pg = PGVector(
                embeddings=embeddings,
                collection_name=_COLLECTION,
                connection=settings.pgvector_url,
                use_jsonb=True,
            )
        elif settings.vector_store == "faiss":
            self._load_faiss()
        else:
            raise ValueError(f"Unknown VECTOR_STORE '{settings.vector_store}'")

    # ---- FAISS helpers -------------------------------------------------
    def _load_faiss(self) -> None:
        from langchain_community.vectorstores import FAISS

        if (self.s.index_dir / "index.faiss").exists():
            self._faiss = FAISS.load_local(
                str(self.s.index_dir), self.emb, allow_dangerous_deserialization=True  # our own files
            )

    def _save_faiss(self) -> None:
        if self._faiss is not None:
            self.s.index_dir.mkdir(parents=True, exist_ok=True)
            self._faiss.save_local(str(self.s.index_dir))

    # ---- public API ----------------------------------------------------
    def add(self, docs: list[Document], ids: list[str]) -> None:
        with self._lock:
            if self.s.vector_store == "pgvector":
                self._pg.add_documents(docs, ids=ids)
                return
            from langchain_community.vectorstores import FAISS

            if self._faiss is None:
                self._faiss = FAISS.from_documents(docs, self.emb, ids=ids)
            else:
                self._faiss.add_documents(docs, ids=ids)
            self._save_faiss()

    def delete(self, ids: list[str]) -> None:
        with self._lock:
            if self.s.vector_store == "pgvector":
                self._pg.delete(ids=ids)
                return
            if self._faiss is not None:
                self._faiss.delete(ids)
                self._save_faiss()

    def search(self, query: str, k: int) -> list[tuple[Document, float]]:
        """Return (document, relevance) pairs; higher relevance is better."""
        if self.s.vector_store == "pgvector":
            hits = self._pg.similarity_search_with_relevance_scores(query, k=k)
            return hits
        if self._faiss is None:
            return []
        hits = self._faiss.similarity_search_with_relevance_scores(query, k=k)
        return hits
