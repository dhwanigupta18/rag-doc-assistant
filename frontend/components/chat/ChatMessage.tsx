"use client";

import type { ChatMessage as ChatMessageType, Citation } from "@/lib/types";
import CitationBadge from "./CitationBadge";

interface ChatMessageProps {
  message: ChatMessageType;
  onCitationClick: (citation: Citation) => void;
}

export default function ChatMessage({ message, onCitationClick }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-2`}>
        <div
          className={`rounded-xl px-4 py-2.5 text-sm leading-relaxed
            ${isUser ? "bg-blue-600 text-white" : "bg-white/8 text-gray-100"}`}
        >
          {message.content}
        </div>

        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 px-1">
            {message.citations.map((citation) => (
              <CitationBadge
                key={citation.chunk_id}
                citation={citation}
                onClick={onCitationClick}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
