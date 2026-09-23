import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WritlynxAI — Secure Personalized Handwriting",
  description: "Prototype research interface for personalized handwriting synthesis, secure style control, and provenance.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
