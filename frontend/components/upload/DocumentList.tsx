"use client";

import type { Document } from "@/lib/types";

interface DocumentListProps {
  documents: Document[];
  isLoading: boolean;
  onSelect: (documentId: string) => void;
}

function StatusBadge({ status }: { status: Document["status"] }) {
  if (status === "ready") {
    return (
      <span className="text-xs px-2 py-0.5 rounded-full bg-green-900/40 text-green-400">
        Ready
      </span>
    );
  }
  if (status === "processing") {
    return (
      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-900/40 text-amber-400 flex items-center gap-1 w-fit">
        <span className="inline-block h-2 w-2 rounded-full border-2 border-amber-400 border-t-transparent animate-spin" />
        Processing
      </span>
    );
  }
  return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-red-900/40 text-red-400">
      Failed
    </span>
  );
}

export default function DocumentList({ documents, isLoading, onSelect }: DocumentListProps) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-16 rounded-lg bg-white/5 animate-pulse" />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-sm">No documents yet.</p>
        <p className="text-xs mt-1">Upload a PDF above to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {documents.map((doc) => {
        const clickable = doc.status === "ready";
        return (
          <div
            key={doc.id}
            onClick={() => clickable && onSelect(doc.id)}
            className={`flex items-center justify-between rounded-lg border border-white/10 p-4 transition
              ${clickable
                ? "cursor-pointer hover:border-white/30 hover:bg-white/5"
                : "opacity-60 cursor-not-allowed"
              }`}
          >
            <div className="min-w-0">
              <p className="text-sm font-medium truncate">{doc.filename}</p>
              <p className="text-xs text-gray-500 mt-0.5">
                {doc.page_count > 0 ? `${doc.page_count} pages · ` : ""}
                {new Date(doc.created_at).toLocaleDateString()}
              </p>
            </div>
            <StatusBadge status={doc.status} />
          </div>
        );
      })}
    </div>
  );
}
