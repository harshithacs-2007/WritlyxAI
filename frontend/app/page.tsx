"use client";

import Link from "next/link";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import { ThemeToggle } from "./theme";

const fadeUp = { hidden: { opacity: 0, y: 24 }, visible: { opacity: 1, y: 0 } };

export default function Home() {
  const heroRef = useRef<HTMLElement | null>(null);
  const processRef = useRef<HTMLElement | null>(null);
  const reduceMotion = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const { scrollYProgress: heroProgress } = useScroll({ target: heroRef, offset: ["start start", "end start"] });
  const paperY = useTransform(heroProgress, [0, 1], [0, reduceMotion ? 0 : 96]);
  const paperRotate = useTransform(heroProgress, [0, 1], [-3, reduceMotion ? -3 : 2]);
  const processProgress = useScroll({ target: processRef, offset: ["start 68%", "end 70%"] });
  const lineScale = useTransform(processProgress.scrollYProgress, [0, 1], [0, 1]);

  return (
    <main className="site-shell">
      <motion.div className="scroll-progress" style={{ scaleX: scrollYProgress }} />
      <nav className="site-nav wrap" aria-label="Main navigation">
        <Link className="wordmark" href="/" aria-label="WritLynxAI home"><span className="wordmark-symbol">w<span>.</span></span><span>WritLynx<span className="wordmark-ai">AI</span></span></Link>
        <div className="nav-links"><a href="#workflows">Workflows</a><a href="#method">Method</a><Link href="/recognize">Recognition</Link></div>
        <ThemeToggle />
        <Link className="nav-cta" href="/studio">Open studio <span aria-hidden="true">↗</span></Link>
      </nav>

      <section className="hero wrap" ref={heroRef}>
        <div className="hero-copy">
          <motion.div className="eyebrow" initial="hidden" animate="visible" variants={fadeUp} transition={{ duration: reduceMotion ? 0 : .6, ease: [0.22, 1, 0.36, 1] }}><span className="eyebrow-mark" /> PERSONAL HANDWRITING RESEARCH</motion.div>
          <motion.h1 initial="hidden" animate="visible" variants={fadeUp} transition={{ duration: reduceMotion ? 0 : .78, delay: reduceMotion ? 0 : .08, ease: [0.22, 1, 0.36, 1] }}>Some things deserve to feel <em>human.</em></motion.h1>
          <motion.p className="hero-description" initial="hidden" animate="visible" variants={fadeUp} transition={{ duration: reduceMotion ? 0 : .72, delay: reduceMotion ? 0 : .16 }}>WritLynxAI explores both sides of handwriting: creating personal, natural-looking writing from digital text, and making difficult handwritten pages easier to read.</motion.p>
          <motion.div className="hero-actions" initial="hidden" animate="visible" variants={fadeUp} transition={{ duration: reduceMotion ? 0 : .65, delay: reduceMotion ? 0 : .22 }}>
            <Link className="button button-light" href="/studio">Create handwriting <span aria-hidden="true">↗</span></Link>
            <Link className="button button-quiet" href="/recognize"><span className="button-play" aria-hidden="true">↳</span> Read a page</Link>
          </motion.div>
          <motion.div className="hero-footnote" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: reduceMotion ? 0 : .8, delay: reduceMotion ? 0 : .5 }}><span className="status-orb" /> Research prototype <span className="footnote-divider">/</span> model integration in progress</motion.div>
        </div>
        <motion.div className="hero-art" style={{ y: paperY, rotate: paperRotate }}>
          <div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" />
          <div className="art-index">STUDY 01 <span>—</span> THE HUMAN MARK</div>
          <div className="paper-shadow paper-shadow-back" />
          <div className="paper-sheet paper-sheet-main">
            <div className="paper-topline"><span>FIELD NOTES</span><span>WR / 026</span></div>
            <div className="paper-handwriting"><div>Every line carries</div><div>a little <i>character.</i></div><div className="paper-subline">The pressure. The pause. The person.</div></div>
            <svg className="paper-scribble" viewBox="0 0 245 78" role="img" aria-label="Decorative pen stroke"><path d="M5 49 C24 7 34 75 55 35 S85 16 86 48 S108 67 125 33 S147 11 150 45 S173 71 191 38 S219 23 240 44" /><path d="M12 67 C55 58 75 72 112 61 S180 70 224 57" /></svg>
            <div className="paper-stamp"><span>W</span><small>STYLE<br />STUDY</small></div>
            <div className="paper-bottomline"><span>INK / PAPER / MEMORY</span><span>01—02</span></div>
          </div>
          <div className="floating-note note-top"><span className="note-dot" /> STYLE, PRESERVED</div>
          <div className="floating-note note-bottom"><span className="note-glyph">Aa</span><span>FROM IMAGE<br /><b>TO MEANING</b></span></div>
        </motion.div>
        <a className="scroll-cue" href="#workflows"><span className="scroll-cue-line" /> Scroll to explore</a>
      </section>

      <section className="workflow-section section-wrap" id="workflows">
        <motion.div className="section-heading" initial="hidden" whileInView="visible" viewport={{ once: true, amount: .3 }} variants={fadeUp} transition={{ duration: reduceMotion ? 0 : .65 }}>
          <div><p className="eyebrow">TWO DIRECTIONS · ONE PURPOSE</p><h2>From words to writing.<br /><em>From writing to words.</em></h2></div>
          <p className="section-intro">Two distinct AI problems, connected by a shared respect for the way people write.</p>
        </motion.div>
        <div className="workflow-grid">
          <motion.article className="workflow-card generation-card" initial="hidden" whileInView="visible" viewport={{ once: true, amount: .2 }} variants={fadeUp} transition={{ duration: reduceMotion ? 0 : .7, delay: reduceMotion ? 0 : .04 }}>
            <div className="workflow-card-top"><span className="workflow-number">01 / GENERATION</span><span className="card-arrow">↗</span></div>
            <div className="workflow-visual generation-visual">
              <div className="mini-paper mini-paper-back" /><div className="mini-paper mini-paper-front"><div className="mini-paper-meta">A NOTE TO REMEMBER</div><div className="mini-hand">Meet me where<br />the light comes in.</div><div className="mini-signature">— with care</div></div>
              <div className="visual-caption">DIGITAL TEXT <span>→</span> PERSONAL STYLE</div>
            </div>
            <div className="workflow-card-copy"><h3>Make digital text feel handwritten.</h3><p>Start with words and a writing sample. Explore a style-conditioned output preview, with authorization and provenance controls around the request.</p><Link className="text-link" href="/studio">Explore generation <span>↗</span></Link></div>
          </motion.article>
          <motion.article className="workflow-card recognition-card" initial="hidden" whileInView="visible" viewport={{ once: true, amount: .2 }} variants={fadeUp} transition={{ duration: reduceMotion ? 0 : .7, delay: reduceMotion ? 0 : .16 }}>
            <div className="workflow-card-top"><span className="workflow-number">02 / RECOGNITION</span><span className="card-arrow">↗</span></div>
            <div className="workflow-visual recognition-visual">
              <div className="manuscript-sheet"><div className="manuscript-tag">ARCHIVE / FRAGMENT 004</div><div className="manuscript-line line-a">In the beginning, the letters</div><div className="manuscript-line line-b">were shaped by hand, not machine.</div><div className="manuscript-line line-c">A record of thought, made visible.</div><div className="scan-focus"><span /><span /><span /><span /></div></div>
              <div className="recognition-float"><span>↳</span><div><b>Image</b><small>to transcript</small></div></div>
            </div>
            <div className="workflow-card-copy"><h3>Make difficult writing easier to read.</h3><p>Prepare a scanned page for transcription. The recognition workspace is ready for a language-specific HTR model; automatic recognition is not connected yet.</p><Link className="text-link" href="/recognize">Explore recognition <span>↗</span></Link></div>
          </motion.article>
        </div>
      </section>

      <section className="method-section" id="method" ref={processRef}>
        <div className="method-layout section-wrap">
          <div className="method-copy"><p className="eyebrow">THE METHOD</p><h2>A careful process.<br /><em>Not a magic button.</em></h2><p>Reliable handwriting AI starts with reliable examples. Each image needs the correct transcript, each style must stay attached to its owner, and each generated result needs a traceable record.</p><Link className="button button-outline" href="/studio">See the prototype <span aria-hidden="true">↗</span></Link></div>
          <div className="method-steps"><motion.div className="method-rail"><motion.div className="method-rail-fill" style={{ scaleY: lineScale }} /></motion.div>
            {[
              ["01", "Collect", "Photograph known text and keep the exact transcript beside it."],
              ["02", "Learn", "Evaluate language-compatible models against verified handwriting samples."],
              ["03", "Control", "Bind a generation request to its user, style, purpose and content."],
              ["04", "Trace", "Keep a provenance record so the prototype output can be inspected."],
            ].map(([number, title, copy], index) => (
              <motion.article className="method-step" key={number} initial={{ opacity: 0, x: reduceMotion ? 0 : 18 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true, amount: .65 }} transition={{ duration: reduceMotion ? 0 : .55, delay: reduceMotion ? 0 : index * .04 }}>
                <span className="step-number">{number}</span><div><h3>{title}</h3><p>{copy}</p></div>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      <section className="language-section section-wrap">
        <motion.div className="language-panel" initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, amount: .25 }} transition={{ duration: reduceMotion ? 0 : .65 }}>
          <div className="language-copy"><p className="eyebrow">BUILT TO GROW</p><h2>Many scripts.<br /><em>Many stories.</em></h2><p>English is a starting point for model exploration. Tamil, Telugu, Hindi and Sanskrit need script-aware datasets and model evaluation. Historical manuscripts remain a longer-term research direction.</p></div>
          <div className="script-grid" aria-label="Planned language support">
            <div className="script-tile"><span>En</span><b>English</b><small>BASELINE</small></div><div className="script-tile script-indic"><span>அ</span><b>Tamil</b><small>DATA PILOT</small></div><div className="script-tile script-indic"><span>తె</span><b>Telugu</b><small>PLANNED</small></div><div className="script-tile script-indic"><span>अ</span><b>Hindi</b><small>PLANNED</small></div><div className="script-tile script-indic"><span>सं</span><b>Sanskrit</b><small>PLANNED</small></div><div className="script-tile script-more"><span>+</span><b>More scripts</b><small>IN TIME</small></div>
          </div>
        </motion.div>
      </section>
      <section className="closing-section wrap"><div><p className="eyebrow">THE WRITLYNXAI WORKSPACE</p><h2>Give every page<br />a way forward.</h2></div><div className="closing-actions"><Link className="button button-light" href="/studio">Start with generation <span>↗</span></Link><Link className="button button-quiet" href="/recognize">Prepare a page <span>↗</span></Link></div></section>
      <footer className="site-footer wrap"><Link className="wordmark" href="/"><span className="wordmark-symbol">w<span>.</span></span><span>WritLynx<span className="wordmark-ai">AI</span></span></Link><p>PERSONAL HANDWRITING · CONTROLLED STYLE · TRACEABLE OUTPUT</p><span className="footer-prototype"><i /> RESEARCH PROTOTYPE</span></footer>
    </main>
  );
}
