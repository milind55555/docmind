# DocMind: Chat With Your Documents (RAG)

A full-stack Retrieval-Augmented Generation app. Upload PDFs, text, CSV or Excel files, then ask questions in plain English. Answers stream back token by token and cite the passages they came from.

**Stack:** Python, FastAPI, LangChain, FAISS (or pgvector), Pandas, OpenAI / Anthropic APIs, React (Vite), Docker, GitHub Actions.

## Architecture

```
React UI --(upload / SSE chat)--> FastAPI
                                    |
   ingestion.py  PDF/TXT/MD -> LangChain text splitter
                 CSV/XLSX   -> Pandas summary + row batches
                                    |
   providers.py  embeddings (fastembed local | OpenAI)
                                    |
   vectorstore.py  FAISS on disk  |  pgvector (Postgres)
                                    |
   rag.py  top-k retrieval -> prompt with numbered excerpts -> LLM (streamed) -> cited answer
```

## Features

- Multi-format ingestion; spreadsheets get a Pandas-generated schema and statistics passage so numeric questions work
- Recursive chunking with overlap, per-chunk metadata (source, page, row range)
- Pluggable embeddings, vector store and LLM via environment variables
- Streaming answers over Server-Sent Events, with expandable source excerpts
- Delete a document and its vectors are removed from the index
- Offline demo mode (`LLM_PROVIDER=mock`) that needs no API key
- Pytest suite, Ruff linting, CI pipeline, Docker Compose

## Run locally

```bash
cp .env.example .env            # set LLM_PROVIDER and your API key
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

Try the files in `sample_data/` first.

## Run with Docker

```bash
cp .env.example .env
docker compose up --build       # UI on :8080, API on :8000
```

### Use pgvector instead of FAISS

```bash
pip install -r backend/requirements-pgvector.txt
# in .env: VECTOR_STORE=pgvector
docker compose --profile pgvector up
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Active providers |
| GET | `/api/documents` | List documents |
| POST | `/api/documents` | Upload and index a file |
| DELETE | `/api/documents/{id}` | Remove a file and its vectors |
| POST | `/api/chat` | SSE stream: `sources`, `token`, `done` |

## Tests

```bash
cd backend && pytest -q && ruff check .
```

## Design notes

- Answers are grounded: the prompt tells the model to use only the retrieved excerpts and to say so when the answer is missing.
- Chunk IDs are `<doc_id>:<n>`, which makes deletion exact in both FAISS and pgvector.
- FAISS is loaded with `allow_dangerous_deserialization` because the index is written by this app only. Do not load index files from untrusted sources.

## Ideas to extend

Hybrid search (BM25 plus vectors), a reranker, per-document filters, user auth, and an evaluation script that measures answer faithfulness.
