import axios from "axios";
import type { Document, ChatMessage, ChatResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

const client = axios.create({
  baseURL: API_BASE,
});

// ---- Documents ----

export async function listDocuments(): Promise<Document[]> {
  const res = await client.get<Document[]>("/documents/");
  return res.data;
}

export async function getDocument(documentId: string): Promise<Document> {
  const res = await client.get<Document>(`/documents/${documentId}`);
  return res.data;
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await client.post<Document>("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

// Returns a URL the browser can load the raw PDF bytes from, for react-pdf
// to render. Not used yet in Phase 6 step 1, but every component that needs
// the actual file (PdfViewer) will call this.
export function getDocumentFileUrl(documentId: string): string {
  return `${API_BASE}/documents/${documentId}/file`;
}

// ---- Chat ----

export async function sendChatMessage(
  documentId: string,
  question: string
): Promise<ChatResponse> {
  const res = await client.post<ChatResponse>(`/chat/${documentId}`, {
    question,
  });
  return res.data;
}

export async function getChatHistory(documentId: string): Promise<ChatMessage[]> {
  const res = await client.get<ChatMessage[]>(`/chat/${documentId}/history`);
  return res.data;
}
