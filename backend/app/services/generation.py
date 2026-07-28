"""
Generates a grounded answer from retrieved chunks using Groq (Llama 3.3),
enforcing a structured JSON output (answer + citations) rather than
free-text citations.

Why structured output matters here: if the LLM just wrote "According to page
3..." in prose, we'd have to parse that back out unreliably. Instead, we ask
the model to return machine-readable citations (chunk_id references) that we
validate against the chunks we actually sent it — so the frontend can later
highlight the *exact* bbox region in the PDF, and we can catch/reject
hallucinated citations that don't match a real chunk_id.
"""
import json

from groq import Groq
from pydantic import BaseModel, ValidationError

from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)


class LLMCitation(BaseModel):
    chunk_id: str


class LLMAnswer(BaseModel):
    answer: str
    citations: list[LLMCitation]


SYSTEM_INSTRUCTION = """You are a document assistant. You answer questions \
using ONLY the provided context chunks from a single document. Do not use \
outside knowledge. If the answer isn't in the provided context, say so \
clearly instead of guessing.

You must respond with ONLY a JSON object in this exact shape, no other text:
{"answer": "your answer here", "citations": [{"chunk_id": "..."}]}

Include a citation for every chunk_id whose content you actually used to \
answer. If you used no chunks (e.g. the answer isn't in the document), \
return an empty citations list."""


def _build_prompt(question: str, chunks: list[dict]) -> str:
    context_blocks = []
    for c in chunks:
        context_blocks.append(
            f'[chunk_id: {c["chunk_id"]}] (page {c["page_number"]})\n{c["text"]}'
        )
    context = "\n\n---\n\n".join(context_blocks)

    return f"""Context chunks from the document:

{context}

Question: {question}

Respond with only the JSON object described in your instructions."""


def _parse_llm_response(raw_text: str) -> LLMAnswer:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    data = json.loads(cleaned)
    return LLMAnswer(**data)


def generate_answer(question: str, chunks: list[dict]) -> dict:
    """
    chunks: output of hybrid_search() — each has chunk_id, page_number, bbox, text.
    Returns {"answer": str, "citations": [{"chunk_id", "page_number", "bbox"}]}
    with citations validated against the chunks actually sent to the LLM.
    """
    if not chunks:
        return {
            "answer": "I couldn't find relevant content in this document to answer that question.",
            "citations": [],
        }

    valid_chunk_ids = {c["chunk_id"] for c in chunks}
    chunk_by_id = {c["chunk_id"]: c for c in chunks}

    prompt = _build_prompt(question, chunks)

    for attempt in range(2):  # one retry if parsing/validation fails
        try:
            completion = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            raw_text = completion.choices[0].message.content
            parsed = _parse_llm_response(raw_text)

            safe_citations = []
            for cite in parsed.citations:
                if cite.chunk_id in valid_chunk_ids:
                    chunk = chunk_by_id[cite.chunk_id]
                    safe_citations.append(
                        {
                            "chunk_id": cite.chunk_id,
                            "page_number": chunk["page_number"],
                            "bbox": chunk["bbox"],
                        }
                    )

            return {"answer": parsed.answer, "citations": safe_citations}

        except (json.JSONDecodeError, ValidationError):
            continue

    return {
        "answer": "Sorry, I had trouble generating a well-formed answer. Please try rephrasing your question.",
        "citations": [],
    }