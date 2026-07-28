"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import ChatMessageComponent from "./ChatMessage";
import { getChatHistory, sendChatMessage } from "@/lib/api";
import type { ChatMessage, Citation } from "@/lib/types";

interface ChatPanelProps {
  documentId: string;
  onCitationClick: (citation: Citation) => void;
}

function tempId() {
  return `temp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export default function ChatPanel({ documentId, onCitationClick }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getChatHistory(documentId)
      .then(setMessages)
      .catch(() => setError("Could not load chat history."))
      .finally(() => setIsLoadingHistory(false));
  }, [documentId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || isSending) return;

    setInput("");
    setError(null);

    // Optimistic: show the user's message immediately, before the backend responds.
    const userMessage: ChatMessage = {
      id: tempId(),
      role: "user",
      content: question,
      citations: null,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);

    try {
      const response = await sendChatMessage(documentId, question);
      const assistantMessage: ChatMessage = {
        id: tempId(),
        role: "assistant",
        content: response.answer,
        citations: response.citations,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch {
      setError("Something went wrong generating an answer. Please try again.");
    } finally {
      setIsSending(false);
    }
  }, [input, isSending, documentId]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {isLoadingHistory ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div key={i} className="h-10 rounded-lg bg-white/5 animate-pulse" />
            ))}
          </div>
        ) : messages.length === 0 ? (
          <p className="text-sm text-gray-500 text-center mt-8">
            Ask a question about this document to get started.
          </p>
        ) : (
          messages.map((message) => (
            <ChatMessageComponent
              key={message.id}
              message={message}
              onCitationClick={onCitationClick}
            />
          ))
        )}

        {isSending && (
          <div className="flex justify-start">
            <div className="rounded-xl px-4 py-2.5 bg-white/8 flex gap-1 items-center">
              <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.3s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce [animation-delay:-0.15s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-gray-400 animate-bounce" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {error && <p className="text-xs text-red-400 px-4 pb-2">{error}</p>}

      <div className="border-t border-white/10 p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Ask a question about this document..."
          className="flex-1 bg-white/5 rounded-lg px-3 py-2 text-sm outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button
          onClick={handleSend}
          disabled={isSending || !input.trim()}
          className="px-4 py-2 rounded-lg bg-blue-600 text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-blue-500 transition"
        >
          Send
        </button>
      </div>
    </div>
  );
}
