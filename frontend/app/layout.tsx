import type { Metadata } from "next";
import Script from "next/script";
import { ThemeProvider } from "./theme";
import "./globals.css";
import "./theme.css";
import "./product.css";

export const metadata: Metadata = {
  title: "WritLynxAI — Handwriting, both ways",
  description: "Explore personalized handwriting generation, handwritten text recognition, and traceable style control with WritLynxAI.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <Script
          id="writlynx-theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: 'try { const saved = localStorage.getItem("writlynx-theme"); document.documentElement.dataset.theme = saved === "light" ? "light" : "dark"; } catch { document.documentElement.dataset.theme = "dark"; }',
          }}
        />
      </head>
      <body><ThemeProvider>{children}</ThemeProvider></body>
    </html>
  );
}
