"""
Quick manual test for the ingestion pipeline, run directly (no API needed).

Usage:
    python test_ingestion.py path/to/some.pdf

This exercises pdf_parser.py and chunker.py in isolation so you can sanity
check chunk boundaries and bbox values before trusting the full API flow.
"""
import sys

from app.services.pdf_parser import extract_blocks
from app.services.chunker import build_chunks


def main():
    if len(sys.argv) != 2:
        print("Usage: python test_ingestion.py path/to/file.pdf")
        sys.exit(1)

    path = sys.argv[1]
    blocks, page_count = extract_blocks(path)
    print(f"Extracted {len(blocks)} text blocks across {page_count} pages\n")

    chunks = build_chunks(blocks)
    print(f"Merged into {len(chunks)} chunks\n")

    for c in chunks[:5]:
        word_count = len(c.text.split())
        preview = c.text[:120].replace("\n", " ")
        print(f"[chunk {c.chunk_index}] page={c.page_number} words={word_count}")
        print(f"  bbox={c.bbox}")
        print(f"  text preview: {preview}...\n")

    if len(chunks) > 5:
        print(f"... and {len(chunks) - 5} more chunks")


if __name__ == "__main__":
    main()
