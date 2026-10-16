"use client";

import { ChangeEvent, useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, useReducedMotion } from "framer-motion";
import { ThemeToggle } from "../theme";

export default function RecognizePage() {
  const reduceMotion = useReducedMotion();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [transcript, setTranscript] = useState("");
  const [attempted, setAttempted] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!file) { setPreviewUrl(""); return; }
    const nextUrl = URL.createObjectURL(file);
    setPreviewUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [file]);

  const chooseFile = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0];
    if (!nextFile) return;
    setError("");
    setAttempted(false);
    setFile(nextFile);
  };
  const requestRecognition = () => {
    if (!file) { setError("Choose a handwriting image before starting."); return; }
    setError("");
    setAttempted(true);
  };
  const reset = () => { setFile(null); setTranscript(""); setAttempted(false); setError(""); };

  return (
    <main className="recognition-shell">
      <header className="workspace-nav wrap">
        <Link className="wordmark" href="/" aria-label="WritLynxAI home"><span className="wordmark-symbol">w<span>.</span></span><span>WritLynx<span className="wordmark-ai">AI</span></span></Link>
        <nav className="workspace-tabs" aria-label="Workspaces"><Link className="workspace-tab" href="/studio">Generation</Link><Link className="workspace-tab active" href="/recognize">Recognition <span className="tab-new">BETA</span></Link></nav>
        <ThemeToggle />
        <Link className="workspace-exit" href="/">Back to overview <span>↗</span></Link>
      </header>
      <section className="workspace-heading recognition-heading wrap">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : .55 }}>
          <p className="eyebrow"><span className="eyebrow-mark" /> WORKSPACE 02 / RECOGNITION</p><h1>Make the hard-to-read<br /><em>legible again.</em></h1>
          <p>Prepare a handwritten page for transcription. This workspace previews the source image and gives you an editable transcript area for the recognition model integration stage.</p>
        </motion.div>
        <div className="workspace-heading-aside"><div className="status-line"><span className="status-orb status-pending" /> Recognition model not connected</div><div className="heading-aside-note">No OCR or AI transcription is run in this prototype. Your image stays in this browser.</div></div>
      </section>

      <section className="recognition-layout wrap">
        <div className="recognition-source">
          <div className="canvas-header"><div><p className="eyebrow">SOURCE IMAGE</p><h2>Choose a page.</h2></div>{file && <button className="text-button" type="button" onClick={reset}>Clear <span>×</span></button>}</div>
          <label className={"recognition-drop " + (file ? "has-source" : "")}>
            <input type="file" accept="image/*" onChange={chooseFile} aria-label="Upload handwritten page image" />
            {previewUrl ? <Image src={previewUrl} alt="Uploaded handwritten page preview" width={1400} height={1200} unoptimized className="recognition-image" /> : <div className="recognition-drop-prompt"><span className="upload-symbol">↑</span><strong>Upload a handwritten page</strong><small>JPG, PNG or WEBP · image remains local</small></div>}
            {file && <span className="source-filename">{file.name} <i>·</i> {(file.size / 1024).toFixed(1)} KB <b>Replace image ↗</b></span>}
          </label>
          <div className="source-info"><span><i className="info-dot" /> SOURCE READY</span><p>For best future recognition results, use a sharp image with even lighting and minimal page skew.</p></div>
          {error && <div className="feedback-error" role="alert">{error}</div>}
          <button className="button button-light recognition-button" type="button" onClick={requestRecognition}>Prepare transcription <span>↗</span></button>
          {attempted && <motion.div className="recognition-notice" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}><span className="notice-icon">i</span><div><strong>Recognition model not connected yet.</strong><p>The image is ready, but the system has not decoded its handwriting. You can type or correct the transcript on the right; the text below is not model-generated.</p></div></motion.div>}
        </div>

        <div className="transcript-panel">
          <div className="canvas-header"><div><p className="eyebrow">DIGITAL TRANSCRIPT</p><h2>Words, made editable.</h2></div><span className="connection-chip"><i /> MANUAL DRAFT</span></div>
          <div className="transcript-editor-wrap">
            <label className="field-label" htmlFor="transcript-text">Transcript text <span>{transcript.length} characters</span></label>
            <textarea id="transcript-text" className="field-control transcript-control" value={transcript} onChange={(event) => setTranscript(event.target.value)} placeholder="The recognized text will appear here once a handwriting-recognition model is integrated. For now, you can type a manual transcription or correct one you already have." />
            <div className="transcript-tools"><span><i className="info-dot" /> {transcript.trim() ? "Draft available" : "No transcript yet"}</span><button className="text-button" type="button" onClick={() => setTranscript("")} disabled={!transcript}>Clear text <span>×</span></button></div>
            <a className={"button button-outline transcript-download " + (!transcript.trim() ? "is-disabled" : "")} href={transcript.trim() ? "data:text/plain;charset=utf-8," + encodeURIComponent(transcript) : undefined} download="writlynxai-transcript.txt" aria-disabled={!transcript.trim()} onClick={(event) => { if (!transcript.trim()) event.preventDefault(); }}>Download transcript <span>↓</span></a>
          </div>
          <div className="transcript-footer"><div className="transcript-footer-mark">Aa</div><div><strong>Ground truth matters.</strong><p>For training and evaluation, each handwriting image must be paired with the exact text written on the page.</p></div></div>
        </div>
      </section>

      <section className="recognition-next wrap"><div><p className="eyebrow">NEXT IN RESEARCH</p><h2>From page capture<br />to trusted text.</h2></div><div className="recognition-next-copy"><p>The next implementation step is connecting a language-appropriate handwritten text recognition model, then evaluating its output against verified transcripts. Historical manuscripts will need separate validation.</p><Link className="text-link" href="/">Explore the WritLynxAI method <span>↗</span></Link></div></section>
      <footer className="workspace-footer wrap"><span>WritLynxAI / Recognition</span><span>Source image → Transcript draft</span><Link href="/studio">Switch to generation ↗</Link></footer>
    </main>
  );
}
