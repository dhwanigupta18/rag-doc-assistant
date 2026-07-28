"""
Merges the raw text blocks from pdf_parser.py into chunks sized for good
retrieval (~300-500 tokens). We merge consecutive blocks *within the same
page* rather than chunking by raw character count, so each chunk still maps
to a real, highlightable region of the page.

We approximate "tokens" with a simple word-count heuristic (roughly 0.75
words per token for English) rather than pulling in a real tokenizer here —
good enough for chunk sizing, not worth the extra dependency at this stage.
"""
from dataclasses import dataclass

from app.services.pdf_parser import ExtractedBlock

TARGET_MIN_WORDS = 150   # roughly ~200 tokens
TARGET_MAX_WORDS = 350   # roughly ~470 tokens


@dataclass
class Chunk:
    page_number: int
    text: str
    bbox: dict
    chunk_index: int


def _union_bbox(a: dict, b: dict) -> dict:
    return {
        "x0": min(a["x0"], b["x0"]),
        "y0": min(a["y0"], b["y0"]),
        "x1": max(a["x1"], b["x1"]),
        "y1": max(a["y1"], b["y1"]),
    }


def build_chunks(blocks: list[ExtractedBlock]) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_index = 0

    current_text_parts: list[str] = []
    current_bbox: dict | None = None
    current_page: int | None = None
    current_word_count = 0

    def flush():
        nonlocal current_text_parts, current_bbox, current_page, current_word_count, chunk_index
        if current_text_parts:
            chunks.append(
                Chunk(
                    page_number=current_page,
                    text=" ".join(current_text_parts).strip(),
                    bbox=current_bbox,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1
        current_text_parts = []
        current_bbox = None
        current_page = None
        current_word_count = 0

    for block in blocks:
        block_word_count = len(block.text.split())

        starting_new_page = current_page is not None and block.page_number != current_page
        would_overflow = current_word_count + block_word_count > TARGET_MAX_WORDS

        if starting_new_page or (would_overflow and current_word_count >= TARGET_MIN_WORDS):
            flush()

        if current_page is None:
            current_page = block.page_number

        current_text_parts.append(block.text)
        current_bbox = block.bbox if current_bbox is None else _union_bbox(current_bbox, block.bbox)
        current_word_count += block_word_count

    flush()  # flush whatever's left after the loop ends

    return chunks
