"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ChatPanel from "@/components/chat/ChatPanel";
import PdfViewer from "@/components/pdf-viewer/PdfViewer";
import { getDocument } from "@/lib/api";
import type { Document, Citation } from "@/lib/types";

export default function WorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.id as string;

  const [document, setDocument] = useState<Document | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);

  useEffect(() => {
    getDocument(documentId)
      .then(setDocument)
      .catch(() => setLoadError("Document not found."));
  }, [documentId]);

  if (loadError) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center gap-3">
        <p className="text-sm text-red-400">{loadError}</p>
        <button
          onClick={() => router.push("/")}
          className="text-sm text-blue-400 hover:underline"
        >
          Back to documents
        </button>
      </main>
    );
  }

  return (
    <main className="h-screen flex flex-col">
      <header className="border-b border-white/10 px-4 py-3 flex items-center gap-3">
        <button
          onClick={() => router.push("/")}
          className="text-sm text-gray-400 hover:text-gray-200"
        >
          ← Back
        </button>
        <h1 className="text-sm font-medium truncate">
          {document?.filename || "Loading..."}
        </h1>
      </header>

      <div className="flex-1 flex min-h-0">
        {/* Left: PDF viewer, highlights the active citation's bbox */}
        <div className="w-1/2 border-r border-white/10 min-h-0">
          <PdfViewer documentId={documentId} activeCitation={activeCitation} />
        </div>

        {/* Right: chat panel */}
        <div className="w-1/2 min-h-0">
          <ChatPanel documentId={documentId} onCitationClick={setActiveCitation} />
        </div>
      </div>
    </main>
  );
}
