"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import UploadDropzone from "@/components/upload/UploadDropzone";
import DocumentList from "@/components/upload/DocumentList";
import { listDocuments, uploadDocument } from "@/lib/api";
import type { Document } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
      setLoadError(null);
    } catch {
      setLoadError("Could not reach the backend. Is it running?");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleUpload = useCallback(
    async (file: File) => {
      const doc = await uploadDocument(file);
      // Prepend immediately so the user sees it without waiting for a refetch.
      setDocuments((prev) => [doc, ...prev]);
    },
    []
  );

  return (
    <main className="min-h-screen max-w-2xl mx-auto px-6 py-16">
      <h1 className="text-2xl font-semibold mb-1">RAG Document Assistant</h1>
      <p className="text-sm text-gray-400 mb-8">
        Upload a PDF, then ask questions grounded in its exact content.
      </p>

      <UploadDropzone onUpload={handleUpload} />

      <div className="mt-10">
        <h2 className="text-sm font-medium text-gray-400 mb-3">Your documents</h2>

        {loadError ? (
          <p className="text-sm text-red-400">{loadError}</p>
        ) : (
          <DocumentList
            documents={documents}
            isLoading={isLoading}
            onSelect={(id) => router.push(`/documents/${id}`)}
          />
        )}
      </div>
    </main>
  );
}
