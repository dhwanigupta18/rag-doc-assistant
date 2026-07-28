"use client";

import { useEffect, useRef } from "react";
import type { BoundingBox } from "@/lib/types";

interface HighlightOverlayProps {
  bbox: BoundingBox;
  scale: number; // rendered pixels per PDF point, e.g. renderedWidth / pageWidthInPoints
}

/**
 * PyMuPDF's block bbox coordinates use a top-left origin with y increasing
 * downward — the same convention as CSS/screen pixel coordinates. That means
 * we can position this overlay with simple left/top math, no y-axis flip
 * needed (unlike raw PDF coordinate space, which is bottom-left origin).
 */
export default function HighlightOverlay({ bbox, scale }: HighlightOverlayProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [bbox]);

  const left = bbox.x0 * scale;
  const top = bbox.y0 * scale;
  const width = (bbox.x1 - bbox.x0) * scale;
  const height = (bbox.y1 - bbox.y0) * scale;

  return (
    <div
      ref={ref}
      className="absolute pointer-events-none rounded-sm animate-[highlight-pulse_1.4s_ease-out_1]"
      style={{
        left,
        top,
        width,
        height,
        backgroundColor: "rgba(250, 204, 21, 0.28)",
        border: "2px solid rgba(250, 204, 21, 0.85)",
      }}
    />
  );
}
