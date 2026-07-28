import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "RAG Document Assistant",
  description: "Chat with your documents using hybrid retrieval + LLM generation",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
