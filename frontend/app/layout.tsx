import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WritLynxAI — Handwriting, both ways",
  description: "Explore personalized handwriting generation, handwritten text recognition, and traceable style control with WritLynxAI.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
