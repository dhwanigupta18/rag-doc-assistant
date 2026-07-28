"use client";

import { useState, useCallback, useRef } from "react";

interface UploadDropzoneProps {
  onUpload: (file: File) => Promise<void>;
}

export default function UploadDropzone({ onUpload }: UploadDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);

      if (!file.name.toLowerCase().endsWith(".pdf")) {
        setError("Only PDF files are supported.");
        return;
      }

      setIsUploading(true);
      try {
        await onUpload(file);
      } catch {
        setError("Upload failed. Please check the backend is running and try again.");
      } finally {
        setIsUploading(false);
      }
    },
    [onUpload]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
      e.target.value = ""; // allow re-uploading the same filename later
    },
    [handleFile]
  );

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition
          ${isDragging ? "border-blue-400 bg-blue-400/5" : "border-white/15 hover:border-white/30"}
          ${isUploading ? "pointer-events-none opacity-60" : ""}`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={handleInputChange}
        />

        {isUploading ? (
          <div className="flex flex-col items-center gap-2">
            <div className="h-6 w-6 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
            <p className="text-sm text-gray-400">
              Uploading and processing — this parses, chunks, and embeds the document...
            </p>
          </div>
        ) : (
          <div>
            <p className="text-sm font-medium">Drop a PDF here, or click to browse</p>
            <p className="text-xs text-gray-500 mt-1">PDF files only</p>
          </div>
        )}
      </div>

      {error && (
        <p className="text-xs text-red-400 mt-2">{error}</p>
      )}
    </div>
  );
}
