"use client";

import type { Citation } from "@/lib/types";

interface CitationBadgeProps {
  citation: Citation;
  onClick: (citation: Citation) => void;
}

export default function CitationBadge({ citation, onClick }: CitationBadgeProps) {
  return (
    <button
      onClick={() => onClick(citation)}
      className="text-xs px-2 py-1 rounded-md bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 transition"
    >
      Page {citation.page_number}
    </button>
  );
}
