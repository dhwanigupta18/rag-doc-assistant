// Mirrors backend/app/schemas/schemas.py — keep these in sync manually
// whenever a backend schema changes.

export interface Document {
  id: string;
  filename: string;
  page_count: number;
  status: "processing" | "ready" | "failed";
  created_at: string;
}

export interface BoundingBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface Citation {
  chunk_id: string;
  page_number: number;
  bbox: BoundingBox;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | null;
  created_at: string;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
}
