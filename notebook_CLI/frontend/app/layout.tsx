import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RAG AI Chat",
  description: "Chat with documents",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#0f172a] text-white">
        {children}
      </body>
    </html>
  );
}