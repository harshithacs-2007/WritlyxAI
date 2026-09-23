'use client';

import { ChangeEvent, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";

type Mode = "mock" | "backend";
type StyleMeta = { styleId: string; seed: number; fileName: string; size: number; sampleCount: number };
type Result = { generationId: string; fingerprint: string; provenanceDigest: string; mode: Mode };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");

async function sha256(text: string) {
  const buffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(buffer)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  if (!API_BASE) throw new Error("Backend URL not configured.");
  const response = await fetch(API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Backend request failed (" + response.status + ")");
  }
  return response.json() as Promise<T>;
}

function seededValue(seed: number, index: number) {
  const x = Math.sin(seed * 12.9898 + index * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

export default function StudioPage() {
  const [file, setFile] = useState<File | null>(null);
  const [style, setStyle] = useState<StyleMeta | null>(null);
  const [text, setText] = useState("Make it look like I wrote it.");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [status, setStatus] = useState("Ready");
  const [result, setResult] = useState<Result | null>(null);
  const [userId, setUserId] = useState("demo-user");
  const [sessionId, setSessionId] = useState("");
  const [error, setError] = useState("");

  const lines = useMemo(() => {
    const words = text.trim().split(/\s+/).slice(0, 24);
    const rows: string[][] = [];
    for (let i = 0; i < words.length; i += 4) rows.push(words.slice(i, i + 4));
    return rows.length ? rows : [["Start", "typing", "to", "generate."]];
  }, [text]);

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (!selected) return;
    setError("");
    setResult(null);
    setIsAnalyzing(true);
    setStatus("Reading sample…");

    const content = selected.name + ":" + selected.size + ":" + selected.lastModified;
    const fingerprint = await sha256(content);
    const seed = parseInt(fingerprint.slice(0, 8), 16) || 1;

    await new Promise((resolve) => setTimeout(resolve, 650));

    setFile(selected);
    setStyle({
      styleId: "STYLE-" + fingerprint.slice(0, 6).toUpperCase(),
      seed,
      fileName: selected.name,
      size: selected.size,
      sampleCount: 1,
    });
    setStatus("Style captured");
    setIsAnalyzing(false);
  };

  const ensureBackendSession = async () => {
    if (!API_BASE) return null;
    if (sessionId) return sessionId;
    try {
      const session = await postJSON<{ session_id: string }>("/sessions", { user_id: userId });
      setSessionId(session.session_id);
      return session.session_id;
    } catch {
      return null;
    }
  };

  const generate = async () => {
    if (!style) return setError("Upload a handwriting sample first.");
    if (!text.trim()) return setError("Enter some text to generate.");

    setError("");
    setIsGenerating(true);
    setStatus("Authorizing style use…");
    const contentHash = await sha256(text.trim());

    try {
      const session = await ensureBackendSession();

      if (API_BASE && session) {
        const styleResponse = await postJSON<{ style_id: string }>("/styles", {
          user_id: userId,
          session_id: session,
          parameters: { seed: style.seed, sample_count: style.sampleCount, source_size: style.size },
          representation_version: "prototype-v1",
        });

        const authorization = await postJSON<{ authorization_id: string }>("/authorize", {
          user_id: userId,
          session_id: session,
          style_id: styleResponse.style_id,
          purpose: "prototype-generation",
          model_version: "prototype-renderer-v1",
          content: text.trim(),
        });

        setStatus("Generating with authorized style…");

        const generation = await postJSON<{ generation_id: string; provenance_digest: string }>("/generate", {
          user_id: userId,
          session_id: session,
          authorization_id: authorization.authorization_id,
          content: text.trim(),
          purpose: "prototype-generation",
          model_version: "prototype-renderer-v1",
        });

        setResult({
          generationId: generation.generation_id,
          fingerprint: contentHash,
          provenanceDigest: generation.provenance_digest,
          mode: "backend",
        });
        setStatus("Generated · provenance recorded");
      } else {
        setStatus("Rendering prototype style…");
        await new Promise((resolve) => setTimeout(resolve, 750));
        const pseudo = await sha256(style.styleId + ":" + contentHash + ":" + style.seed);
        setResult({
          generationId: "GEN-DEMO-" + pseudo.slice(0, 8).toUpperCase(),
          fingerprint: contentHash,
          provenanceDigest: pseudo,
          mode: "mock",
        });
        setStatus("Generated · local prototype");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Generation failed.");
      setStatus("Generation blocked");
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <main className="studio-shell">
      <header className="studio-nav">
        <Link className="brand" href="/"><span className="brand-mark">W</span>WritlynxAI</Link>
        <div className="studio-nav-center"><span className="section-active">Studio</span><span>Provenance</span><span>Research</span></div>
        <div className="status-chip"><i /> Prototype environment</div>
      </header>

      <div className="studio-grid">
        <aside className="control-panel">
          <div className="panel-label">01 / CAPTURE STYLE</div>
          <h1>Bring your handwriting in.</h1>
          <p className="panel-copy">Upload one sample to create a deterministic prototype style representation.</p>

          <label className="upload-box">
            <input type="file" accept="image/*,.pdf" onChange={handleUpload} />
            <span className="upload-icon">+</span>
            <strong>{file ? "Replace sample" : "Upload sample"}</strong>
            <small>PNG, JPG, PDF · prototype only</small>
          </label>

          {isAnalyzing && (
            <div className="progress-card">
              <div className="scan-line" /><div><span>ANALYZER</span><strong>Extracting style signal…</strong></div>
            </div>
          )}

          {style && !isAnalyzing && (
            <motion.div className="style-card" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
              <div className="card-head"><span>STYLE READY</span><span className="green-dot" /></div>
              <strong>{style.styleId}</strong>
              <div className="meta-grid">
                <div><span>SOURCE</span><b>{style.fileName}</b></div>
                <div><span>SAMPLES</span><b>{style.sampleCount}</b></div>
                <div><span>REP</span><b>prototype-v1</b></div>
                <div><span>SEED</span><b>{String(style.seed).slice(0, 6)}</b></div>
              </div>
            </motion.div>
          )}

          <div className="divider" />
          <div className="panel-label">02 / GENERATE</div>

          <label className="field-label">Prototype user</label>
          <input className="field" value={userId} onChange={(event) => setUserId(event.target.value)} placeholder="demo-user" />

          <label className="field-label">Text</label>
          <textarea className="field textarea" value={text} onChange={(event) => setText(event.target.value)} maxLength={5000} placeholder="Type what you want written…" />

          {error && <div className="error-box">{error}</div>}

          <button className="button primary full" disabled={isGenerating} onClick={generate}>
            {isGenerating ? "Authorizing + generating…" : "Generate handwriting"} <span>↗</span>
          </button>

          <div className="status-line"><span>Status</span><strong>{status}</strong></div>
        </aside>

        <section className="canvas-panel">
          <div className="canvas-toolbar">
            <div><span className="panel-label">LIVE OUTPUT</span><h2>Generation workspace</h2></div>
            <span className={"mode-chip " + (result?.mode === "backend" ? "is-live" : "")}>
              {result?.mode === "backend" ? "FASTAPI CONNECTED" : "LOCAL PROTOTYPE"}
            </span>
          </div>

          <div className="paper-stage">
            {!result ? (
              <div className="empty-state">
                <div className="empty-doodle">W</div>
                <h3>Your generated page will land here.</h3>
                <p>Upload a sample, enter text, then run the generation flow.</p>
                <div className="flow-mini"><span>capture</span><b>→</b><span>authorize</span><b>→</b><span>generate</span><b>→</b><span>trace</span></div>
              </div>
            ) : (
              <motion.div className="generated-paper" initial={{ opacity: 0, scale: 0.98, rotate: -0.3 }} animate={{ opacity: 1, scale: 1, rotate: 0 }}>
                <div className="paper-meta">WRTLYX / {result.generationId}</div>
                <div className="handwriting-block">
                  {lines.map((row, rowIndex) => (
                    <div className="writing-row" key={rowIndex}>
                      {row.map((word, wordIndex) => {
                        const jitter = style ? seededValue(style.seed, rowIndex * 7 + wordIndex) : 0.5;
                        return (
                          <span
                            key={word + wordIndex}
                            style={{
                              transform: "rotate(" + ((jitter - 0.5) * 2.4) + "deg) translateY(" + ((jitter - 0.5) * 3) + "px)",
                              letterSpacing: (-0.025 + jitter * 0.025) + "em",
                            }}
                          >
                            {word}
                          </span>
                        );
                      })}
                    </div>
                  ))}
                </div>
                <div className="paper-footer-note">prototype renderer · style-conditioned simulation</div>
              </motion.div>
            )}
          </div>

          <div className="provenance-panel">
            <div className="prov-heading">
              <div><span className="panel-label">03 / PROVENANCE</span><h3>Generation record</h3></div>
              <span className="lock-tag">BOUND</span>
            </div>
            <div className="prov-grid">
              <div><span>GENERATION</span><b>{result?.generationId ?? "—"}</b></div>
              <div><span>STYLE</span><b>{style?.styleId ?? "—"}</b></div>
              <div><span>CONTENT SHA-256</span><b>{result ? result.fingerprint.slice(0, 18) + "…" : "—"}</b></div>
              <div><span>PROVENANCE DIGEST</span><b>{result ? result.provenanceDigest.slice(0, 18) + "…" : "—"}</b></div>
            </div>
            <p className="prototype-note">
              {result?.mode === "backend"
                ? "Backend mode: authorization was issued and consumed before the generation record was created."
                : "Local mode: the UI demonstrates the same intended flow without claiming production-grade security."}
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
