# RAG Document Assistant — Phase 1 scaffold

Contextual document intelligence system: hybrid retrieval (BM25 + vector search) +
LLM generation with source-highlighted citations.

This is the **Phase 1** setup — infra and skeleton only. No ingestion, retrieval, or
chat logic yet (that's Phases 2–5). The goal of this phase is: backend running,
frontend running, database and vector store reachable, and the frontend can hit the
backend's `/health` endpoint successfully.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker + Docker Compose

## 1. Start infrastructure (Postgres + Qdrant)

```bash
cd backend
docker compose up -d
```

Verify:
- Postgres on `localhost:5432`
- Qdrant dashboard on `http://localhost:6333/dashboard`

## 2. Backend setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY and JWT_SECRET_KEY

uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` — you should see the FastAPI interactive docs
with `/health`, `/documents`, and `/chat` endpoints listed. On startup, tables are
auto-created in Postgres (users, documents, chunks, chat_messages).

## 3. Frontend setup

```bash
cd frontend
npm install

cp .env.local.example .env.local

npm run dev
```

Visit `http://localhost:3000` — you should see "Backend status: ok" if the backend
is running correctly. This confirms the frontend can reach the backend over CORS.

## Project structure

```
backend/
  app/
    main.py           # FastAPI app entrypoint
    core/              # config, db session
    models/            # SQLAlchemy ORM models
    schemas/           # Pydantic request/response schemas
    routers/           # API route handlers (currently stubs beyond /health)
    services/          # business logic (ingestion, retrieval, generation) — Phase 2+
  docker-compose.yml   # Postgres + Qdrant
  requirements.txt

frontend/
  app/                 # Next.js app router pages
  components/          # (empty — built out in Phase 6)
  lib/                 # (empty — API client helpers go here)
```

## What's next

- **Phase 2**: implement `/documents/upload`, PDF parsing with PyMuPDF (text +
  bounding boxes), chunking, embedding generation, and storing vectors in Qdrant.
- **Phase 3**: hybrid retrieval (BM25 + vector search + reranker).
- **Phase 4**: LLM generation with structured JSON citations.
- **Phase 5**: wire it into `/chat/{document_id}` with persistence.
- **Phase 6**: build out the real frontend — upload UI, chat interface, PDF viewer
  with highlight overlay.

## Milestone check for Phase 1

- [ ] `docker compose up -d` runs without errors
- [ ] `http://localhost:8000/docs` loads and shows all routers
- [ ] `http://localhost:8000/health` returns `{"status": "ok"}`
- [ ] `http://localhost:3000` shows "Backend status: ok"
- [ ] Postgres has empty `users`, `documents`, `chunks`, `chat_messages` tables
      (check via `docker exec -it rag_postgres psql -U rag_user -d rag_db -c "\dt"`)

---

## Phase 2 — Document ingestion pipeline

New pieces added this phase:

- `app/services/pdf_parser.py` — extracts text blocks + bounding boxes from a PDF using PyMuPDF
- `app/services/chunker.py` — merges blocks into ~200-470 token chunks, preserving page + bbox
- `app/services/embeddings.py` — loads `sentence-transformers` model, embeds chunk text
- `app/core/vectorstore.py` — Qdrant client + collection setup
- `app/services/ingestion.py` — orchestrates the full pipeline and writes to Postgres + Qdrant
- `app/core/deps.py` — **temporary** dev-user stand-in until real auth is built (Phase "auth")
- `app/routers/documents.py` — now has real `POST /documents/upload`, `GET /documents/`, `GET /documents/{id}`

### 1. Install new dependencies

Requirements.txt already included `pymupdf`, `sentence-transformers`, and `qdrant-client` from
Phase 1, but if you haven't reinstalled since then:

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

The first time `sentence-transformers` loads the embedding model, it'll download it from
Hugging Face (a few hundred MB) — this happens automatically on first use and is cached after.

### 2. Test parsing + chunking in isolation (fast feedback loop)

Before going through the API, sanity-check the parsing/chunking logic directly against any PDF
you have lying around:

```bash
cd backend
source venv/bin/activate
python test_ingestion.py /path/to/some.pdf
```

You should see chunk previews with page numbers and bbox coordinates printed to the console.
If chunk sizes look way too small or way too large, that's the `TARGET_MIN_WORDS` /
`TARGET_MAX_WORDS` constants in `chunker.py` to tune.

### 3. Test the full upload endpoint

Make sure Docker (Postgres + Qdrant) and the backend are running, then:

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@/path/to/some.pdf"
```

You should get back JSON with `"status": "ready"` and a `page_count`. If `"status": "failed"`,
check the backend terminal for the traceback.

Then confirm data landed in both stores:

```bash
# Postgres — should show chunk rows
docker exec -it rag_postgres psql -U rag_user -d rag_db -c "SELECT page_number, chunk_index, left(text, 60) FROM chunks LIMIT 5;"
```

Check Qdrant's dashboard at `http://localhost:6333/dashboard` — you should see your collection
(`document_chunks`) with points matching your chunk count.

### Milestone check for Phase 2

- [ ] `test_ingestion.py` prints sensible chunks with page numbers + bbox for a real PDF
- [ ] `POST /documents/upload` returns `"status": "ready"`
- [ ] Postgres `chunks` table has rows with real text and bbox JSON
- [ ] Qdrant dashboard shows matching points in the `document_chunks` collection

---

## Phase 3 — Hybrid retrieval

New pieces added this phase:

- `app/services/bm25_index.py` — keyword search, with an in-memory index **cached per document**
  (rebuilt only when that document's chunks change, not on every query — see the module docstring
  for the tradeoffs of this vs. true incremental indexing)
- `app/services/vector_search.py` — dense vector search against Qdrant, scoped to one document
- `app/services/reranker.py` — cross-encoder reranking of the fused shortlist
- `app/services/retrieval.py` — orchestrates it all: BM25 + vector search → Reciprocal Rank Fusion
  → rerank → final top chunks
- `GET /documents/{document_id}/search?q=...` — debug endpoint to inspect retrieval results directly
  (no LLM involved yet — that's Phase 4)

### Test it

Make sure Docker + backend are running, and you've already uploaded a document (Phase 2). Grab its
`id` from the upload response or from:
```bash
docker exec -it rag_postgres psql -U rag_user -d rag_db -c "SELECT id, filename FROM documents;"
```

Then query it:
```bash
curl "http://localhost:8000/documents/<document_id>/search?q=your+question+here"
```

For example, against a resume:
```bash
curl "http://localhost:8000/documents/2313b8bb-cee2-4792-881e-24ac4ddeaadb/search?q=what+frontend+skills+does+this+person+have"
```

The first query will be slower — it downloads the `bge-reranker-base` cross-encoder model
(~280MB) the first time it's used, same as the embedding model did in Phase 2.

You should get back JSON with a `results` array — each item has `chunk_id`, `page_number`, `bbox`,
`text`, and `rerank_score`. The top result should actually be relevant to your query.

### Milestone check for Phase 3

- [ ] `/documents/{id}/search?q=...` returns results, not an empty array
- [ ] The top-ranked chunk is genuinely relevant to the query (try a few different questions)
- [ ] Try a query with an exact keyword/number from the document (BM25's strength) and a more
      conceptual/paraphrased query (vector search's strength) — both should return sensible results
