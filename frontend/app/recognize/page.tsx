"use client";

import { ChangeEvent, useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion, useReducedMotion } from "framer-motion";
import { ThemeToggle } from "../theme";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
const DEMO_USER_ID = "demo-user";

type RecognitionJob = {
  job_id: string;
  status: string;
  original_filename: string;
  image_sha256: string;
  model_id: string;
  lines_recognized: number;
  transcript: string;
  created_at: string;
};

type RecognitionSession = { userId: string; sessionId: string; expiresAt: number };

async function getRecognitionSession(): Promise<RecognitionSession> {
  if (!API_BASE) throw new Error("The backend URL is not configured. Set NEXT_PUBLIC_API_BASE_URL in frontend/.env.local.");
  const cachedId = window.localStorage.getItem("writlynx-recognition-session");
  const cachedExpiry = Number(window.localStorage.getItem("writlynx-recognition-session-expiry") || 0);
  if (cachedId && cachedExpiry > Date.now() + 30000) {
    return { userId: DEMO_USER_ID, sessionId: cachedId, expiresAt: cachedExpiry };
  }

  const response = await fetch(API_BASE + "/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: DEMO_USER_ID }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Could not create a recognition session.");
  const expiresAt = Date.parse(data.expires_at);
  window.localStorage.setItem("writlynx-recognition-session", data.session_id);
  window.localStorage.setItem("writlynx-recognition-session-expiry", String(expiresAt));
  return { userId: DEMO_USER_ID, sessionId: data.session_id, expiresAt };
}

async function loadRecentRuns(session: RecognitionSession): Promise<RecognitionJob[]> {
  if (!API_BASE) return [];
  const query = new URLSearchParams({
    user_id: session.userId,
    session_id: session.sessionId,
    limit: "8",
  });
  const response = await fetch(API_BASE + "/recognitions?" + query.toString());
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Could not load recognition history.");
  return data as RecognitionJob[];
}

export default function RecognizePage() {
  const reduceMotion = useReducedMotion();
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [transcript, setTranscript] = useState("");
  const [attempted, setAttempted] = useState(false);
  const [isRecognizing, setIsRecognizing] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<RecognitionJob | null>(null);
  const [recentRuns, setRecentRuns] = useState<RecognitionJob[]>([]);
  const [historyReady, setHistoryReady] = useState(false);

  useEffect(() => {
    if (!file) { setPreviewUrl(""); return; }
    const nextUrl = URL.createObjectURL(file);
    setPreviewUrl(nextUrl);
    return () => URL.revokeObjectURL(nextUrl);
  }, [file]);

  useEffect(() => {
    if (!API_BASE) return;
    let cancelled = false;
    getRecognitionSession()
      .then(loadRecentRuns)
      .then((runs) => {
        if (!cancelled) { setRecentRuns(runs); setHistoryReady(true); }
      })
      .catch(() => {
        if (!cancelled) setHistoryReady(true);
      });
    return () => { cancelled = true; };
  }, []);

  const chooseFile = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0];
    if (!nextFile) return;
    setError("");
    setAttempted(false);
    setResult(null);
    if (nextFile.size > 8 * 1024 * 1024) {
      setFile(null);
      setError("Choose an image smaller than 8 MB.");
      return;
    }
    if (nextFile.type && !["image/png", "image/jpeg", "image/webp"].includes(nextFile.type)) {
      setFile(null);
      setError("Use a PNG, JPEG, or WEBP image.");
      return;
    }
    setFile(nextFile);
  };

  const requestRecognition = async () => {
    if (!file) { setError("Choose a handwriting image before starting."); return; }
    if (!API_BASE) {
      setError("The English recognition model runs in the backend. Configure NEXT_PUBLIC_API_BASE_URL in frontend/.env.local and start the backend.");
      return;
    }
    setError("");
    setAttempted(false);
    setIsRecognizing(true);
    try {
      const session = await getRecognitionSession();
      const form = new FormData();
      form.append("file", file, file.name);
      form.append("user_id", session.userId);
      form.append("session_id", session.sessionId);
      const response = await fetch(API_BASE + "/recognize", { method: "POST", body: form });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Recognition request failed.");

      const job = data as RecognitionJob;
      setResult(job);
      setTranscript(job.transcript);
      setAttempted(true);
      setRecentRuns((runs) => [job, ...runs.filter((run) => run.job_id !== job.job_id)].slice(0, 8));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Recognition failed. Check that the backend is running and retry.");
    } finally {
      setIsRecognizing(false);
    }
  };

  const reset = () => { setFile(null); setTranscript(""); setAttempted(false); setError(""); setResult(null); };
  const openSavedRun = (job: RecognitionJob) => {
    setTranscript(job.transcript);
    setResult(job);
    setAttempted(job.status === "COMPLETED");
    setError("");
  };

  return (
    <main className="recognition-shell">
      <header className="workspace-nav wrap">
        <Link className="wordmark" href="/" aria-label="WritLynxAI home"><span className="wordmark-symbol">w<span>.</span></span><span>WritLynx<span className="wordmark-ai">AI</span></span></Link>
        <nav className="workspace-tabs" aria-label="Workspaces"><Link className="workspace-tab" href="/studio">Generation</Link><Link className="workspace-tab active" href="/recognize">Recognition</Link></nav>
        <ThemeToggle />
        <Link className="workspace-exit" href="/">Back to overview <span>↗</span></Link>
      </header>

      <section className="workspace-heading recognition-heading wrap">
        <motion.div initial={{ opacity: 0, y: reduceMotion ? 0 : 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: reduceMotion ? 0 : .45 }}>
          <p className="eyebrow"><span className="eyebrow-mark" /> ENGLISH HANDWRITING RECOGNITION</p>
          <h1>Make your handwriting<br /><em>editable text.</em></h1>
          <p>Upload a clear, single-column English page. TrOCR reads the writing; you can correct the transcript and save it as a text file.</p>
        </motion.div>
        <div className="workspace-heading-aside">
          <div className="status-line"><span className={"status-orb " + (API_BASE ? "status-pending" : "")} /> {API_BASE ? "English model · backend mode" : "Backend not configured"}</div>
          <div className="heading-aside-note">{API_BASE ? "First use downloads model weights to the backend's Hugging Face cache. The source image is processed in memory, not retained." : "Start the FastAPI backend and set NEXT_PUBLIC_API_BASE_URL to enable AI recognition."}</div>
        </div>
      </section>

      <section className="recognition-layout wrap">
        <div className="recognition-source">
          <div className="canvas-header"><div><p className="eyebrow">1 / SOURCE IMAGE</p><h2>Choose a page.</h2></div>{file && <button className="text-button" type="button" onClick={reset}>Clear <span>×</span></button>}</div>
          <label className={"recognition-drop " + (file ? "has-source" : "")}>
            <input type="file" accept="image/png,image/jpeg,image/webp" onChange={chooseFile} aria-label="Upload handwritten page image" />
            {previewUrl ? <Image src={previewUrl} alt="Uploaded handwritten page preview" width={1400} height={1200} unoptimized className="recognition-image" /> : <div className="recognition-drop-prompt"><span className="upload-symbol">↑</span><strong>Upload a handwritten page</strong><small>PNG, JPEG or WEBP · maximum 8 MB</small></div>}
            {file && <span className="source-filename">{file.name} <i>·</i> {(file.size / 1024).toFixed(1)} KB <b>Replace image ↗</b></span>}
          </label>
          <div className="source-info"><span><i className="info-dot" /> {file ? "IMAGE READY" : "AWAITING IMAGE"}</span><p>Best results: one column, legible English, strong contrast, even lighting and visible spaces between lines. Printed text, multi-column layouts and heavily skewed pages may be inaccurate.</p></div>
          {error && <div className="feedback-error" role="alert">{error}</div>}
          <button className="button button-light recognition-button" type="button" onClick={requestRecognition} disabled={isRecognizing || !file}>
            {isRecognizing ? <><span className="button-spinner" /> Recognizing…</> : <>Recognize English text <span>↗</span></>}
          </button>
          {isRecognizing && <div className="recognition-notice"><span className="notice-icon">…</span><div><strong>Running the recognition model.</strong><p>The first request may take longer while the backend downloads model weights. Keep this page open.</p></div></div>}
          {attempted && result && <motion.div className="recognition-notice" initial={{ opacity: 0, y: reduceMotion ? 0 : 8 }} animate={{ opacity: 1, y: 0 }}><span className="notice-icon">✓</span><div><strong>English recognition complete.</strong><p>{result.lines_recognized} text lines were processed by {result.model_id}. Review the output before using it; recognition can make mistakes.</p></div></motion.div>}
        </div>

        <div className="transcript-panel">
          <div className="canvas-header"><div><p className="eyebrow">2 / DIGITAL TRANSCRIPT</p><h2>Review and correct.</h2></div><span className={"connection-chip " + (result?.status === "COMPLETED" ? "connection-live" : "")}><i /> {result?.status === "COMPLETED" ? "MODEL OUTPUT" : "EDITABLE TEXT"}</span></div>
          <div className="transcript-editor-wrap">
            <label className="field-label" htmlFor="transcript-text">Transcript text <span>{transcript.length} characters</span></label>
            <textarea id="transcript-text" className="field-control transcript-control" value={transcript} onChange={(event) => setTranscript(event.target.value)} placeholder="Your English transcript will appear here after recognition. You can also type a transcription manually." />
            <div className="transcript-tools"><span><i className="info-dot" /> {transcript.trim() ? "Draft available" : "No transcript yet"}</span><button className="text-button" type="button" onClick={() => setTranscript("")} disabled={!transcript}>Clear text <span>×</span></button></div>
            <a className={"button button-outline transcript-download " + (!transcript.trim() ? "is-disabled" : "")} href={transcript.trim() ? "data:text/plain;charset=utf-8," + encodeURIComponent(transcript) : undefined} download="writlynxai-transcript.txt" aria-disabled={!transcript.trim()} onClick={(event) => { if (!transcript.trim()) event.preventDefault(); }}>Download transcript <span>↓</span></a>
            {result && <div className="recognition-record"><span>SAVED JOB</span><b>{result.job_id}</b><span>IMAGE SHA-256</span><b>{result.image_sha256.slice(0, 24)}…</b><span>MODEL</span><b>{result.model_id}</b><small>The transcript and checksum are saved in SQLite. The source image is not stored.</small></div>}
          </div>
          <div className="transcript-footer"><div className="transcript-footer-mark">Aa</div><div><strong>Human review stays in the loop.</strong><p>TrOCR is a pretrained baseline. Correct names, punctuation and ambiguous words before relying on the result.</p></div></div>
        </div>
      </section>

      {recentRuns.length > 0 && (
        <section className="recognition-history wrap" aria-labelledby="recognition-history-title">
          <div className="recognition-history-head"><div><p className="eyebrow">LOCAL SQLITE HISTORY</p><h2 id="recognition-history-title">Recent recognition runs</h2></div><span>{recentRuns.length} saved {recentRuns.length === 1 ? "run" : "runs"}</span></div>
          <div className="recognition-history-list">
            {recentRuns.map((job) => (
              <article className="recognition-history-item" key={job.job_id}>
                <div><strong>{job.original_filename}</strong><p>{job.transcript ? job.transcript.slice(0, 110) : "No transcript saved"}{job.transcript.length > 110 ? "…" : ""}</p><small>{new Date(job.created_at).toLocaleString()} · {job.lines_recognized} lines · {job.status}</small></div>
                <button className="text-button" type="button" onClick={() => openSavedRun(job)} disabled={!job.transcript}>Open <span>↗</span></button>
              </article>
            ))}
          </div>
        </section>
      )}
      {historyReady && API_BASE && recentRuns.length === 0 && <p className="recognition-history-empty wrap">Completed runs will appear here. SQLite stores the transcript and image checksum, not the uploaded page.</p>}

      <footer className="workspace-footer wrap"><span>WritLynxAI / English recognition</span><span>TrOCR · transcript review · SQLite history</span><Link href="/studio">Switch to generation ↗</Link></footer>
    </main>
  );
}
