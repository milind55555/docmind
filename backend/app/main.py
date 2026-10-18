"""FastAPI entrypoint for DocMind."""
from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .config import get_settings
from .ingestion import SUPPORTED, build_documents
from .providers import get_embeddings, get_llm
from .rag import sources_payload, stream_answer
from .registry import Registry
from .vectorstore import VectorStore


class ChatTurn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    app.state.settings = s
    app.state.registry = Registry(s.registry_path)
    app.state.store = VectorStore(s, get_embeddings(s))
    app.state.llm = get_llm(s)
    yield


app = FastAPI(title="DocMind API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    s = app.state.settings
    return {
        "status": "ok",
        "llm_provider": s.llm_provider,
        "embeddings_provider": s.embeddings_provider,
        "vector_store": s.vector_store,
    }


@app.get("/api/documents")
def list_documents():
    return app.state.registry.list()


@app.post("/api/documents", status_code=201)
async def upload_document(file: UploadFile = File(...)):
    s = app.state.settings
    data = await file.read()
    if len(data) > s.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File too large (max {s.max_upload_mb} MB).")
    doc_id = uuid.uuid4().hex[:12]
    try:
        docs = build_documents(
            file.filename or "upload", data, doc_id, s.chunk_size, s.chunk_overlap, s.csv_rows_per_chunk
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    ids = [f"{doc_id}:{i}" for i in range(len(docs))]
    app.state.store.add(docs, ids)
    return app.state.registry.add(doc_id, file.filename or "upload", len(data), ids) | {"chunk_ids": None}


@app.delete("/api/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str):
    item = app.state.registry.get(doc_id)
    if not item:
        raise HTTPException(404, "Document not found.")
    app.state.store.delete(item["chunk_ids"])
    app.state.registry.remove(doc_id)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Server-sent events: one `sources` event, many `token` events, then `done`."""
    s = app.state.settings
    hits = app.state.store.search(req.question, s.top_k)
    history = [t.model_dump() for t in req.history]

    async def events():
        yield f"event: sources\ndata: {json.dumps(sources_payload(hits))}\n\n"
        try:
            async for token in stream_answer(app.state.llm, req.question, history, hits):
                yield f"event: token\ndata: {json.dumps(token)}\n\n"
        except Exception as e:  # surface provider errors (bad key, rate limit) to the UI
            yield f"event: error\ndata: {json.dumps(str(e))}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/supported")
def supported():
    return sorted(SUPPORTED)
