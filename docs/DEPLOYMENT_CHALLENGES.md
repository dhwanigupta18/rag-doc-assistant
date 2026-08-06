# Deployment Challenges & Engineering Decisions

This document records the real problems encountered while deploying this
project to production, and how each was diagnosed and resolved. Written
deliberately as a debugging log, not a cleaned-up success story — the goal
is to show the reasoning process, not just the final working state.

## 1. Free-tier memory limits forced a local-vs-hosted ML architecture decision

**Problem**: The backend ran fine locally but crashed with
`Ran out of memory (used over 512MB)` on Render's free tier whenever a
document was uploaded.

**Diagnosis**: `sentence-transformers` pulls in PyTorch as a dependency.
Even before any model is loaded, importing PyTorch alone consumes a large
share of a 512MB container. Combined with FastAPI, SQLAlchemy, the Postgres
driver, and the Qdrant client already resident in memory, there wasn't
enough headroom left to load an embedding model.

**First mitigation attempt**: Switched to `fastembed` (ONNX Runtime instead
of PyTorch) — smaller, no GPU dependency. This reduced memory pressure but
still hit the same OOM error on upload, just less severely.

**Root fix**: Moved embedding generation and reranking off the server
entirely, calling Jina AI's hosted embeddings and reranking APIs over HTTP
instead of running any model locally. This made the backend a genuinely
lightweight service with no ML inference footprint at all.

**Why this is a good answer in a viva**: It demonstrates iterative
diagnosis (tried a cheaper local option first, measured that it still
failed, then made a more fundamental architecture change) rather than
guessing at a single fix. It's also a legitimate real-world pattern —
separating stateless inference from application logic is exactly how
production systems scale.

## 2. Cloudflare R2 → Supabase Storage: a constraint-driven pivot, not a technical one

**Problem**: Chosen initially for persistent file storage (see #3 below),
Cloudflare R2 required a credit card on file to activate, even for its free
tier — a hard blocker for a project deliberately built without adding any
payment method (mirroring the same reasoning that led to using Groq instead
of a paid LLM API earlier in the project).

**Fix**: Switched to Supabase Storage, which offers an S3-compatible API
(so the `boto3`-based client code required almost no changes) with no card
requirement.

**Why this is worth mentioning**: Not every engineering decision is driven
by technical merit — sometimes a constraint (cost, sign-up friction) is the
deciding factor, and recognizing that early avoids wasted effort. The
S3-compatibility of both providers meant the switch cost minutes, not hours,
because the storage layer had already been abstracted behind a single
`storage.py` module.

## 3. Discovering the hosting platform's filesystem is ephemeral

**Problem**: Documents uploaded successfully and worked immediately, but
after any redeploy, previously-uploaded PDFs returned 404 when the PDF
viewer tried to fetch them — even though their database records still
showed `status: ready`.

**Diagnosis**: Render (like most container-based hosts) uses ephemeral
storage — anything written to local disk is wiped whenever the container
restarts or a new deploy happens. Postgres and Qdrant were already safe
because they're separate managed services; the raw uploaded files had never
been given the same treatment and were still being written to local disk
(`UPLOAD_DIR`).

**Fix**: Moved file storage to Supabase Storage (see #2), so uploaded PDFs
now persist independently of the backend container's lifecycle, consistent
with how the database and vector store were already architected.

**Why this is a good finding**: It's a subtle, easy-to-miss class of bug —
everything appears to work in initial testing (upload → parse → chat all
succeed in the same session), and the failure only surfaces later, on the
next deploy. Catching and fixing this before final submission avoided
shipping a system that would silently lose all uploaded documents on the
very next code change.

## 4. A missing route decorator broke one endpoint silently

**Problem**: After switching file serving from `FileResponse` to
`RedirectResponse` (to support presigned URLs), the `/documents/{id}/file`
endpoint started returning a generic `{"detail":"Not Found"}` — indicating
no matching route at all, not an application-level 404.

**Diagnosis**: During the manual edit, the `@router.get("/{document_id}/file")`
decorator above the function definition had been dropped. Python's syntax
was still entirely valid — a plain function with no decorator is legal —
so nothing crashed at startup. FastAPI simply never registered it as a
route, and the failure only appeared when that specific endpoint was called.

**Why this is worth knowing for a viva**: It's a good example of a bug
class that unit tests focused only on business logic would miss, but that
integration-level testing (calling the actual endpoint) catches
immediately. It reinforces the value of testing the deployed API surface
directly (`/docs`, real HTTP calls), not just the underlying functions.

## 5. Recurring theme: stale or mismatched environment variables

Several separate incidents throughout deployment traced back to the same
root cause — an environment variable on Render holding an old, wrong, or
accidentally-swapped value (a JWT secret pasted into `EMBEDDING_MODEL`, a
local Docker Postgres URL left in place after switching to Neon, a
reranker model name left over from a previous provider). Each was resolved
by directly inspecting the value in Render's dashboard rather than assuming
the last edit had applied correctly.

**Why this pattern matters**: Environment-variable drift between "what I
think is set" and "what is actually set" is one of the most common real
deployment issues, precisely because the application code itself is
correct — the bug lives entirely in configuration, invisible to code
review. The practical lesson: when a deployed service behaves differently
from local, verify the actual live configuration first, before re-reading
code that hasn't changed.

## 6. Qdrant Cloud requires an explicit payload index for filtering

**Problem**: Retrieval worked perfectly against local Docker Qdrant, but
failed with `Index required but not found for "document_id"` against
Qdrant Cloud, despite identical application code.

**Diagnosis**: Local Qdrant (via Docker) silently allows filtering on any
payload field. The managed cloud version enforces that filtered fields have
an explicit index created first — a stricter, more production-realistic
constraint that only surfaced once real cloud infrastructure was involved.

**Fix**: Added an explicit `create_payload_index()` call for `document_id`
during collection setup.

## 7. Presigned URL signature mismatch against a non-AWS S3-compatible provider

**Problem**: After moving to Supabase Storage, the PDF viewer's fetch to a
presigned URL returned `AccessDenied: Missing signature` from Supabase's
storage gateway.

**Diagnosis**: `boto3`'s default signing behavior is tuned for AWS itself;
against a non-AWS S3-compatible endpoint, it can produce a URL that omits
or malforms the expected signature unless the signature version and
addressing style are set explicitly.

**Fix**: Explicitly configured `signature_version="s3v4"` and
`addressing_style="path"` on the `boto3` client.

## Summary for a viva answer

If asked "what was the hardest part of this project," the honest answer is:
not the RAG pipeline itself (retrieval, reranking, and generation all
worked close to correctly on the first well-reasoned attempt), but making
that pipeline run reliably on real, resource-constrained infrastructure —
diagnosing memory limits from stack traces, working around vendor-specific
constraints (mandatory billing, ephemeral storage, strict indexing
requirements), and tracing configuration drift between environments. These
are exactly the skills that distinguish "a model that works in a notebook"
from "a system that works in production."