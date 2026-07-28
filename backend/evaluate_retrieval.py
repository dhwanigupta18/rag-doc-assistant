"""
Evaluates retrieval quality against a small hand-labeled ground-truth set
(evaluation/eval_dataset.json), comparing three retrieval strategies:

  1. BM25 only        - keyword search alone
  2. Vector only       - dense embedding search alone
  3. Hybrid + rerank   - the full Phase 3 pipeline (RRF fusion + cross-encoder)

For each question, "correct" means at least one returned chunk's page_number
is in that question's expected_pages list. This is a coarse but honest proxy
for relevance — checking exact chunk_id would require re-deriving ground
truth every time chunking parameters change, which isn't worth the fragility
for a project at this scale.

Metrics reported per method:
  - Hit@5   : fraction of questions where a correct chunk appears anywhere
              in the top 5 results
  - MRR@5   : mean reciprocal rank of the first correct chunk (0 if none in
              top 5) — rewards ranking the right answer higher, not just
              including it somewhere in the top 5

Usage:
    python evaluate_retrieval.py
"""
import json

from app.core.db import SessionLocal
from app.services.bm25_index import bm25_search
from app.services.vector_search import vector_search
from app.services.retrieval import hybrid_search, FINAL_TOP_K
from app.models.models import Chunk

EVAL_SET_PATH = "evaluation/eval_dataset.json"


def _is_correct(page_number: int, expected_pages: list[int]) -> bool:
    return page_number in expected_pages


def _reciprocal_rank(pages_in_rank_order: list[int], expected_pages: list[int]) -> float:
    for rank, page in enumerate(pages_in_rank_order, start=1):
        if page in expected_pages:
            return 1.0 / rank
    return 0.0


def _pages_for_chunk_ids(db, chunk_ids: list[str]) -> list[int]:
    """Look up page numbers for BM25/vector results, which only return chunk_ids."""
    chunks = db.query(Chunk).filter(Chunk.id.in_(chunk_ids)).all()
    page_by_id = {c.id: c.page_number for c in chunks}
    return [page_by_id[cid] for cid in chunk_ids if cid in page_by_id]


def evaluate():
    with open(EVAL_SET_PATH) as f:
        eval_data = json.load(f)

    document_id = eval_data["document_id"]
    questions = eval_data["questions"]

    db = SessionLocal()

    results = {
        "bm25_only": {"hits": 0, "rr_sum": 0.0},
        "vector_only": {"hits": 0, "rr_sum": 0.0},
        "hybrid_rerank": {"hits": 0, "rr_sum": 0.0},
    }
    per_question_rows = []

    try:
        for q in questions:
            question_text = q["question"]
            expected_pages = q["expected_pages"]

            # --- BM25 only ---
            bm25_results = bm25_search(db, document_id, question_text, top_k=FINAL_TOP_K)
            bm25_chunk_ids = [cid for cid, _score in bm25_results]
            bm25_pages = _pages_for_chunk_ids(db, bm25_chunk_ids)

            # --- Vector only ---
            vec_results = vector_search(document_id, question_text, top_k=FINAL_TOP_K)
            vec_chunk_ids = [cid for cid, _score in vec_results]
            vec_pages = _pages_for_chunk_ids(db, vec_chunk_ids)

            # --- Full hybrid + rerank (Phase 3 pipeline) ---
            hybrid_results = hybrid_search(db, document_id, question_text)
            hybrid_pages = [r["page_number"] for r in hybrid_results]

            row = {"id": q["id"], "question": question_text, "expected": expected_pages}

            for method_name, pages in [
                ("bm25_only", bm25_pages),
                ("vector_only", vec_pages),
                ("hybrid_rerank", hybrid_pages),
            ]:
                hit = any(_is_correct(p, expected_pages) for p in pages)
                rr = _reciprocal_rank(pages, expected_pages)
                results[method_name]["hits"] += int(hit)
                results[method_name]["rr_sum"] += rr
                row[method_name] = {"pages": pages, "hit": hit, "rr": round(rr, 2)}

            per_question_rows.append(row)

    finally:
        db.close()

    n = len(questions)
    summary = {}
    for method_name, agg in results.items():
        summary[method_name] = {
            "hit_at_5": round(agg["hits"] / n, 3),
            "mrr_at_5": round(agg["rr_sum"] / n, 3),
        }

    # ---- Print a readable report ----
    print(f"\nEvaluated {n} questions against document {document_id}\n")
    print(f"{'Method':<18}{'Hit@5':<10}{'MRR@5':<10}")
    print("-" * 38)
    for method_name, m in summary.items():
        print(f"{method_name:<18}{m['hit_at_5']:<10}{m['mrr_at_5']:<10}")

    print("\nPer-question breakdown:")
    for row in per_question_rows:
        print(f"\n[{row['id']}] {row['question']}")
        print(f"  expected pages: {row['expected']}")
        for method_name in ["bm25_only", "vector_only", "hybrid_rerank"]:
            r = row[method_name]
            mark = "✓" if r["hit"] else "✗"
            print(f"  {method_name:<15} {mark}  pages={r['pages']}  rr={r['rr']}")

    # ---- Save full results to disk for the report ----
    output = {"summary": summary, "per_question": per_question_rows}
    with open("evaluation/results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nFull results saved to evaluation/results.json")


if __name__ == "__main__":
    evaluate()
