"""
Extracts text from a PDF while preserving *where* each piece of text sits on
the page (bounding box). This is the piece that makes source-highlighting
possible later in the frontend PDF viewer — without bbox data, we could only
say "this came from page 4," not "this came from this exact paragraph."
"""
import fitz  # PyMuPDF


class ExtractedBlock:
    def __init__(self, page_number: int, text: str, bbox: dict):
        self.page_number = page_number  # 1-indexed for human-friendly display
        self.text = text
        self.bbox = bbox  # {x0, y0, x1, y1} in PDF point coordinates

    def __repr__(self):
        return f"<Block page={self.page_number} chars={len(self.text)}>"


def extract_blocks(file_path: str) -> tuple[list[ExtractedBlock], int]:
    """
    Returns (blocks, page_count).
    Each block corresponds to one text block as detected by PyMuPDF's layout
    analysis — roughly a paragraph. We keep these as the base unit before
    chunking, since blocks already respect natural document structure better
    than a raw character-count split would.
    """
    doc = fitz.open(file_path)
    blocks: list[ExtractedBlock] = []

    for page_index, page in enumerate(doc):
        page_number = page_index + 1
        raw = page.get_text("dict")

        for block in raw["blocks"]:
            if block.get("type") != 0:
                # type 0 = text block, type 1 = image block — skip images here
                continue

            block_text_parts = []
            for line in block.get("lines", []):
                line_text = "".join(span["text"] for span in line.get("spans", []))
                if line_text.strip():
                    block_text_parts.append(line_text)

            block_text = " ".join(block_text_parts).strip()
            if not block_text:
                continue

            x0, y0, x1, y1 = block["bbox"]
            blocks.append(
                ExtractedBlock(
                    page_number=page_number,
                    text=block_text,
                    bbox={"x0": x0, "y0": y0, "x1": x1, "y1": y1},
                )
            )

    page_count = doc.page_count
    doc.close()
    return blocks, page_count
