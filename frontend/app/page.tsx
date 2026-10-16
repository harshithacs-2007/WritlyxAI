"use client";

import Link from "next/link";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { useRef, useState } from "react";
import { ThemeToggle } from "./theme";

export default function Home() {
  const heroRef = useRef<HTMLElement | null>(null);
  const toolsRef = useRef<HTMLElement | null>(null);
  const reduceMotion = useReducedMotion();
  const [demoText, setDemoText] = useState("Every line carries a little character.");
  const [paperStyle, setPaperStyle] = useState<"letter" | "notes">("letter");
  const { scrollYProgress } = useScroll();
  const { scrollYProgress: heroProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const { scrollYProgress: toolsProgress } = useScroll({
    target: toolsRef,
    offset: ["start 72%", "end 65%"],
  });
  const paperY = useTransform(heroProgress, [0, 1], [0, reduceMotion ? 0 : 42]);
  const paperRotate = useTransform(heroProgress, [0, 1], [-1.6, reduceMotion ? -1.6 : 1.1]);
  const toolProgress = useTransform(toolsProgress, [0, 1], [0, 1]);

  return (
    <main className="product-home">
      <motion.div className="product-scroll-progress" style={{ scaleX: scrollYProgress }} />
      <header className="product-topbar wrap">
        <Link className="wordmark" href="/" aria-label="WritLynxAI home">
          <span className="wordmark-symbol">w<span>.</span></span>
          <span>WritLynx<span className="wordmark-ai">AI</span></span>
        </Link>
        <nav className="product-nav-links" aria-label="Product navigation">
          <Link href="/studio">Create</Link>
          <Link href="/recognize">Recognize</Link>
        </nav>
        <div className="product-nav-actions">
          <ThemeToggle />
          <Link className="product-nav-button" href="/studio">Open studio <span aria-hidden="true">↗</span></Link>
        </div>
      </header>

      <section className="product-hero wrap" ref={heroRef}>
        <div className="product-hero-copy">
          <div className="product-kicker"><span /> HANDWRITING, BOTH WAYS</div>
          <h1>Make text feel<br /><em>human again.</em></h1>
          <p className="product-hero-description">
            Turn digital words into a handwriting-style preview, or prepare a handwritten page for editable text. One workspace for both directions.
          </p>
          <div className="product-hero-actions">
            <Link className="product-primary-button" href="/studio">Create handwriting <span aria-hidden="true">↗</span></Link>
            <Link className="product-secondary-button" href="/recognize">Read a handwritten page <span aria-hidden="true">→</span></Link>
          </div>
          <div className="product-availability"><span className="product-status-dot" /> Interactive prototype <span className="product-status-divider">·</span> AI model connections in progress</div>
        </div>

        <motion.section className="product-demo" style={{ y: paperY, rotate: paperRotate }} aria-label="Interactive handwriting preview demo">
          <div className="product-demo-header">
            <div className="product-window-dots" aria-hidden="true"><i /><i /><i /></div>
            <span>QUICK PREVIEW</span>
            <span className="product-demo-badge">ILLUSTRATIVE</span>
          </div>
          <div className="product-demo-body">
            <div className={"product-preview-paper " + (paperStyle === "notes" ? "is-notes" : "is-letter")}>
              <div className="product-paper-topline"><span>PERSONAL NOTES</span><span>WR / 01</span></div>
              <div className="product-paper-copy">{demoText.trim() || "Your words will appear here."}</div>
              <div className="product-paper-rule" />
              <div className="product-paper-footer"><span>INK · PAPER · YOU</span><span>PREVIEW</span></div>
            </div>
          </div>
          <div className="product-demo-controls">
            <label className="product-demo-label" htmlFor="quick-preview-text">Try your own words</label>
            <textarea id="quick-preview-text" value={demoText} onChange={(event) => setDemoText(event.target.value)} maxLength={180} rows={2} placeholder="Type a short note…" />
            <div className="product-demo-control-row">
              <div className="product-paper-switch" role="group" aria-label="Choose preview paper style">
                <button type="button" className={paperStyle === "letter" ? "is-active" : ""} aria-pressed={paperStyle === "letter"} onClick={() => setPaperStyle("letter")}>Letter</button>
                <button type="button" className={paperStyle === "notes" ? "is-active" : ""} aria-pressed={paperStyle === "notes"} onClick={() => setPaperStyle("notes")}>Notes</button>
              </div>
              <Link className="product-demo-open" href={"/studio?text=" + encodeURIComponent(demoText)}>Continue in studio ↗</Link>
            </div>
          </div>
          <p className="product-demo-disclaimer">Live text preview only. Real AI handwriting generation is not connected yet.</p>
        </motion.section>

        <a className="product-scroll-cue" href="#product-tools"><span /> Explore the tools</a>
      </section>

      <section className="product-tools section-wrap" id="product-tools" ref={toolsRef}>
        <div className="product-tools-intro">
          <div className="product-kicker"><span /> YOUR WORKSPACE</div>
          <h2>Start with what<br />you need to do.</h2>
          <p>No complicated setup. Choose a task to open its workspace and continue from there.</p>
          <div className="product-tools-progress" aria-hidden="true"><motion.span style={{ scaleY: toolProgress }} /></div>
        </div>

        <div className="product-tool-list">
          <motion.article className="product-tool-card" initial={{ opacity: 0, y: reduceMotion ? 0 : 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.3 }} transition={{ duration: reduceMotion ? 0 : 0.48 }}>
            <div className="product-tool-card-head"><span className="product-tool-icon" aria-hidden="true">Aa</span><span className="product-tool-label">01 <i /> GENERATION</span></div>
            <h3>Give your text a handwriting style.</h3>
            <p>Upload a writing sample, enter your words, and inspect a paper preview with a request record.</p>
            <div className="product-tool-meta"><span>Sample image</span><span>Text input</span><span>Preview</span></div>
            <Link className="product-tool-link" href="/studio">Open handwriting studio <span aria-hidden="true">↗</span></Link>
          </motion.article>

          <motion.article className="product-tool-card" initial={{ opacity: 0, y: reduceMotion ? 0 : 22 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: 0.3 }} transition={{ duration: reduceMotion ? 0 : 0.48, delay: reduceMotion ? 0 : 0.08 }}>
            <div className="product-tool-card-head"><span className="product-tool-icon product-tool-icon-recognition" aria-hidden="true">文</span><span className="product-tool-label">02 <i /> RECOGNITION</span></div>
            <h3>Make a handwritten page editable.</h3>
            <p>Preview a scanned page, type or correct its transcription, then save the text as a file.</p>
            <div className="product-tool-meta"><span>Image preview</span><span>Editable text</span><span>Download</span></div>
            <Link className="product-tool-link" href="/recognize">Open recognition workspace <span aria-hidden="true">↗</span></Link>
          </motion.article>
        </div>
      </section>

      <section className="product-bottom wrap">
        <div className="product-bottom-mark" aria-hidden="true">w.</div>
        <div><h2>Made for the page in front of you.</h2><p>Use the current prototype to explore the workflow. Model-powered handwriting generation and automatic recognition remain future integration steps.</p></div>
        <Link className="product-bottom-link" href="/studio">Go to studio ↗</Link>
      </section>

      <footer className="product-footer wrap">
        <Link className="wordmark" href="/"><span className="wordmark-symbol">w<span>.</span></span><span>WritLynx<span className="wordmark-ai">AI</span></span></Link>
        <span>HANDWRITING TOOLS · INTERACTIVE PROTOTYPE</span>
        <div><Link href="/studio">Generation</Link><Link href="/recognize">Recognition</Link></div>
      </footer>
    </main>
  );
}
