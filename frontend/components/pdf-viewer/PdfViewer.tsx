"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Document as PdfDocument, Page, pdfjs } from "react-pdf";
// Text/annotation layer CSS isn't imported since both layers are disabled
// below (renderTextLayer/renderAnnotationLayer=false) — we only need the
// rendered page canvas plus our own HighlightOverlay on top of it.
import HighlightOverlay from "./HighlightOverlay";
import { getDocumentFileUrl } from "@/lib/api";
import type { Citation } from "@/lib/types";

// react-pdf renders PDFs via PDF.js under the hood, which needs its own
// worker script to parse/render off the main thread. Without this, pages
// either fail to render or throw a cryptic "worker not configured" error.
// Loading it from a CDN keeps us from having to vendor the file ourselves.
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfViewerProps {
  documentId: string;
  activeCitation: Citation | null;
}

export default function PdfViewer({ documentId, activeCitation }: PdfViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(600);
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageWidthPoints, setPageWidthPoints] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const fileUrl = getDocumentFileUrl(documentId);

  useEffect(() => {
    const measure = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth - 32);
      }
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  useEffect(() => {
    if (activeCitation) {
      setCurrentPage(activeCitation.page_number);
    }
  }, [activeCitation]);

  const handleDocumentLoad = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
  }, []);

  const handlePageLoad = useCallback((page: { originalWidth: number }) => {
    setPageWidthPoints(page.originalWidth);
  }, []);

  const scale = pageWidthPoints ? containerWidth / pageWidthPoints : 1;

  const showHighlightOnThisPage =
    activeCitation && activeCitation.page_number === currentPage;

  return (
    <div ref={containerRef} className="h-full overflow-y-auto p-4">
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
          disabled={currentPage <= 1}
          className="text-xs px-2 py-1 rounded bg-white/5 disabled:opacity-30 hover:bg-white/10"
        >
          ← Prev
        </button>
        <span className="text-xs text-gray-400">
          Page {currentPage}{numPages ? ` of ${numPages}` : ""}
        </span>
        <button
          onClick={() => setCurrentPage((p) => Math.min(numPages, p + 1))}
          disabled={currentPage >= numPages}
          className="text-xs px-2 py-1 rounded bg-white/5 disabled:opacity-30 hover:bg-white/10"
        >
          Next →
        </button>
      </div>

      {loadError ? (
        <p className="text-sm text-red-400">{loadError}</p>
      ) : (
        <PdfDocument
          file={fileUrl}
          onLoadSuccess={handleDocumentLoad}
          onLoadError={() => setLoadError("Could not load this PDF.")}
          loading={<div className="h-96 rounded-lg bg-white/5 animate-pulse" />}
        >
          <div className="relative inline-block">
            <Page
              pageNumber={currentPage}
              width={containerWidth}
              onLoadSuccess={handlePageLoad}
              renderTextLayer={false}
              renderAnnotationLayer={false}
            />
            {showHighlightOnThisPage && pageWidthPoints && (
              <HighlightOverlay bbox={activeCitation!.bbox} scale={scale} />
            )}
          </div>
        </PdfDocument>
      )}
    </div>
  );
}
