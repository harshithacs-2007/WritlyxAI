"use client";

import { ChangeEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, useReducedMotion } from "framer-motion";
import { ThemeToggle } from "../theme";

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
  const response = await fetch(API_BASE + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
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
  const reduceMotion = useReducedMotion();
  const [file, setFile] = useState<File | null>(null);
  const [samplePreview, setSamplePreview] = useState("");
  const [style, setStyle] = useState<StyleMeta | null>(null);
  const [text, setText] = useState("Make it look like I wrote it.");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [status, setStatus] = useState("Ready for a sample");
  const [result, setResult] = useState<Result | null>(null);
  const [userId, setUserId] = useState("demo-user");
  const [sessionId, setSessionId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!file || !file.type.startsWith("image/")) { setSamplePreview(""); return; }
    const objectUrl = URL.createObjectURL(file);
    setSamplePreview(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  const lines = useMemo(() => {
    const words = text.trim().split(/\s+/).filter(Boolean).slice(0, 48);
    const rows: string[][] = [];
    for (let i = 0; i < words.length; i += 5) rows.push(words.slice(i, i + 5));
    return rows.length ? rows : [["Your", "words", "will", "appear", "here."]];
  }, [text]);

  const handleUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (!selected) return;
    setError("");
    setResult(null);
    setFile(selected);
    setIsAnalyzing(true);
    setStatus("Preparing sample preview");
    const fingerprint = await sha256(selected.name + ":" + selected.size + ":" + selected.lastModified);
    const seed = parseInt(fingerprint.slice(0, 8), 16) || 1;
    await new Promise((resolve) => setTimeout(resolve, 380));
    setStyle({ styleId: "STYLE-" + fingerprint.slice(0, 6).toUpperCase(), seed, fileName: selected.name, size: selected.size, sampleCount: 1 });
    setStatus("Sample loaded · encoder not connected");
    setIsAnalyzing(false);
  };

  const ensureBackendSession = async () => {
    if (!API_BASE) return null;
    if (sessionId) return sessionId;
    const session = await postJSON<{ session_id: string }>("/sessions", { user_id: userId });
    setSessionId(session.session_id);
    return session.session_id;
  };

  const generate = async () => {
    if (!style) { setError("Upload a handwriting sample before generating a preview."); return; }
    if (!text.trim()) { setError("Enter the text you want to preview."); return; }
    if (!userId.trim()) { setError("Enter a prototype user ID."); return; }
    setError("");
    setIsGenerating(true);
    setStatus(API_BASE ? "Checking backend authorization" : "Preparing local visual simulation");
    const contentHash = await sha256(text.trim());
    try {
      const session = await ensureBackendSession();
      if (API_BASE && session) {
        const styleResponse = await postJSON<{ style_id: string }>("/styles", {
          user_id: userId.trim(), session_id: session,
          parameters: { seed: style.seed, sample_count: style.sampleCount, source_size: style.size },
          representation_version: "prototype-v1",
        });
        const authorization = await postJSON<{ authorization_id: string }>("/authorize", {
          user_id: userId.trim(), session_id: session, style_id: styleResponse.style_id,
          purpose: "prototype-generation", model_version: "prototype-renderer-v1", content: text.trim(),
        });
        setStatus("Consuming one-time authorization");
        const generation = await postJSON<{ generation_id: string; provenance_digest: string }>("/generate", {
          user_id: userId.trim(), session_id: session, authorization_id: authorization.authorization_id,
          content: text.trim(), purpose: "prototype-generation", model_version: "prototype-renderer-v1",
        });
        setResult({ generationId: generation.generation_id, fingerprint: contentHash, provenanceDigest: generation.provenance_digest, mode: "backend" });
        setStatus("Authorization consumed · provenance recorded");
      } else {
        await new Promise((resolve) => setTimeout(resolve, 520));
        const pseudo = await sha256(style.styleId + ":" + contentHash + ":" + style.seed);
        setResult({ generationId: "GEN-DEMO-" + pseudo.slice(0, 8).toUpperCase(), fingerprint: contentHash, provenanceDigest: pseudo, mode: "mock" });
        setStatus("Preview created · local simulation");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Generation failed.");
      setStatus("Request blocked");
    } finally { setIsGenerating(false); }
  };

  const resetSample = () => { setFile(null); setStyle(null); setResult(null); setError(""); setStatus("Ready for a sample"); };

  return (
    <main className="workspace-shell">
      <header className="workspace-nav wrap">
        <Link className="wordmark" href="/" aria-label="WritLynxAI home"><span className="wordmark-symbol">w<span>.</span></span><span>WritLynx<span className="wordmark-ai">AI</span></span></Link>
        <nav className="workspace-tabs" aria-label="Workspaces"><Link className="workspace-tab active" href="/studio">Generation</Link><Link className="workspace-tab" href="/recognize">Recognition <span className="tab-new">BETA</span></Link></nav>
        <ThemeToggle />
        <Link className="workspace-exit" href="/">Back to overview <span>↗</span></Link>
      </header>

      <section className="workspace-heading wrap">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : .55 }}>
          <p className="eyebrow"><span className="eyebrow-mark" /> WORKSPACE 01 / GENERATION</p>
          <h1>Give your words<br /><em>a human hand.</em></h1>
          <p>Load a handwriting sample, enter your text, and inspect the generation flow. Style encoding and the trained handwriting model are not yet connected.</p>
        </motion.div>
        <div className="workspace-heading-aside"><div className="status-line"><span className="status-orb" /> {API_BASE ? "Backend configured" : "Local prototype mode"}</div><div className="heading-aside-note">No uploaded file is sent to a model in this prototype renderer.</div></div>
      </section>

      <section className="studio-layout wrap">
        <aside className="studio-sidebar">
          <div className="panel-section-head"><span>01</span><div><h2>Capture a style</h2><p>Choose a clear photo of handwriting.</p></div></div>
          <label className="upload-zone">
            <input type="file" accept="image/*,.pdf" onChange={handleUpload} aria-label="Upload a handwriting sample" />
            {samplePreview ? <Image src={samplePreview} alt="Preview of uploaded handwriting sample" width={1200} height={800} unoptimized className="upload-preview" /> : <span className="upload-symbol">↑</span>}
            <strong>{file ? file.name : "Drop your writing here"}</strong><small>{file ? "Sample metadata loaded" : "Browse files · PNG, JPG or PDF"}</small>{file && <span className="upload-replace">Choose another ↗</span>}
          </label>
          {isAnalyzing && <motion.div className="inline-progress" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}><span className="progress-sweep" /><div><small>LOCAL PREVIEW</small><strong>Preparing file details…</strong></div></motion.div>}
          {style && !isAnalyzing && <motion.div className="sample-record" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <div className="sample-record-top"><span className="small-label">SAMPLE REFERENCE</span><span className="sample-state">LOADED</span></div><b>{style.styleId}</b>
            <div className="sample-meta"><span>File size</span><strong>{(style.size / 1024).toFixed(1)} KB</strong><span>Style encoder</span><strong>Not connected</strong></div>
            <button className="text-button" onClick={resetSample} type="button">Remove sample <span>×</span></button>
          </motion.div>}
          <div className="sidebar-divider" />
          <div className="panel-section-head"><span>02</span><div><h2>Write your text</h2><p>Content is hashed before the request flow.</p></div></div>
          <label className="field-label" htmlFor="prototype-user">Prototype user ID</label><input id="prototype-user" className="field-control" value={userId} maxLength={64} onChange={(event) => setUserId(event.target.value)} placeholder="demo-user" />
          <label className="field-label field-label-spaced" htmlFor="generation-text">Your text <span>{text.length}/5000</span></label><textarea id="generation-text" className="field-control textarea-control" value={text} onChange={(event) => setText(event.target.value)} maxLength={5000} placeholder="Type the words you want to see…" />
          {error && <div className="feedback-error" role="alert">{error}</div>}
          <button className="button button-light generate-button" disabled={isGenerating} onClick={generate} type="button">{isGenerating ? <><span className="button-spinner" /> Working…</> : <>Create preview <span>↗</span></>}</button>
          <p className="sidebar-disclaimer">The current paper preview uses deterministic browser styling. It is not AI-generated handwriting.</p>
        </aside>

        <section className="studio-canvas" aria-label="Generation preview and provenance">
          <div className="canvas-header"><div><p className="eyebrow">OUTPUT CANVAS</p><h2>Your page, in progress.</h2></div><span className={"connection-chip " + (result?.mode === "backend" ? "connection-live" : "")}><i /> {result?.mode === "backend" ? "CONTROL LAYER USED" : "VISUAL SIMULATION"}</span></div>
          <div className="canvas-stage">
            {!result ? <motion.div className="canvas-empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: reduceMotion ? 0 : .4 }}><div className="empty-mark"><span>w</span><i /></div><h3>Room for your words.</h3><p>Your preview will appear here after you load a sample and create a request.</p><div className="mini-pipeline"><span>sample</span><b>→</b><span>authorize</span><b>→</b><span>preview</span><b>→</b><span>trace</span></div></motion.div> : (
              <motion.div className="output-paper" initial={{ opacity: 0, y: 16, rotate: -1.4 }} animate={{ opacity: 1, y: 0, rotate: -.3 }} transition={{ duration: reduceMotion ? 0 : .6, ease: [.2,.8,.2,1] }}>
                <div className="output-paper-top"><span>WRTLYNX / {result.generationId}</span><span>WORKING PROTOTYPE</span></div>
                <div className="output-writing">{lines.map((row, rowIndex) => <div className="output-writing-row" key={rowIndex}>{row.map((word, wordIndex) => {
                  const jitter = style ? seededValue(style.seed, rowIndex * 11 + wordIndex) : .5;
                  return <span key={word + wordIndex} style={{ transform: "rotate(" + ((jitter - .5) * 2.3) + "deg) translateY(" + ((jitter - .5) * 3) + "px)", letterSpacing: (-.025 + jitter * .025) + "em" }}>{word}</span>;
                })}</div>)}</div>
                <div className="output-paper-footer"><span>SIMULATED PEN VARIATION</span><span>NOT A MODEL OUTPUT</span></div>
              </motion.div>
            )}
          </div>
          <div className="provenance-card">
            <div className="provenance-title"><div><p className="eyebrow">03 / PROVENANCE</p><h3>Request record</h3></div><span className="integrity-tag">SHA-256 <i>✓</i></span></div>
            <div className="provenance-grid"><div><span>GENERATION ID</span><b>{result?.generationId ?? "Waiting for request"}</b></div><div><span>STYLE REFERENCE</span><b>{style?.styleId ?? "No sample"}</b></div><div><span>CONTENT FINGERPRINT</span><b>{result ? result.fingerprint.slice(0, 18) + "…" : "—"}</b></div><div><span>PROVENANCE DIGEST</span><b>{result ? result.provenanceDigest.slice(0, 18) + "…" : "—"}</b></div></div>
            <div className="record-bottom"><span className="record-status"><i /> {status}</span><p>{result?.mode === "backend" ? "FastAPI authorization was issued and consumed; the backend stored a prototype provenance record." : "Local mode creates a demo fingerprint only. No backend authorization or persistent record is claimed."}</p></div>
          </div>
        </section>
      </section>
      <footer className="workspace-footer wrap"><span>WritLynxAI / Generation</span><span>Personal style · Controlled use · Provenance</span><Link href="/recognize">Switch to recognition ↗</Link></footer>
    </main>
  );
}
