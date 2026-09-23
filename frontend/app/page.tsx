import Link from "next/link";

const principles = [
  ["01", "Personal style", "Learn a writer-specific visual style from a small sample set."],
  ["02", "Controlled use", "Bind each generation request to an authorized user, session and purpose."],
  ["03", "Traceable output", "Attach generation metadata so every prototype output has a provenance trail."],
];

export default function Home() {
  return (
    <main className="landing">
      <nav className="nav container">
        <Link className="brand" href="/"><span className="brand-mark">W</span><span>WritlynxAI</span></Link>
        <div className="nav-right">
          <span className="research-pill"><i /> Research prototype</span>
          <Link className="nav-link" href="/studio">Open studio</Link>
        </div>
      </nav>

      <section className="hero container">
        <div className="hero-copy">
          <p className="eyebrow">PERSONALIZED HANDWRITING · CONTROLLED STYLE · PROVENANCE</p>
          <h1>Handwriting that feels <em>personal.</em> Control that stays deliberate.</h1>
          <p className="hero-text">
            WritlynxAI explores personalized handwriting synthesis with a security layer around the learned style representation — so the system can reason about who may use a style, for what purpose, and which generation produced the output.
          </p>
          <div className="hero-actions">
            <Link className="button primary" href="/studio">Try the prototype <span>↗</span></Link>
            <a className="button ghost" href="#research">See the research direction</a>
          </div>
          <div className="hero-proof"><span>●</span> Browser-first demo · FastAPI control layer · SQLite prototype persistence</div>
        </div>

        <div className="hero-visual">
          <div className="paper-stack">
            <div className="paper back-paper" />
            <div className="paper main-paper">
              <span className="paper-note">STYLE 001 / PROTOTYPE</span>
              <div className="paper-name">Dear future me,</div>
              <div className="paper-line">your handwriting should still</div>
              <div className="paper-line">look like <span>you.</span></div>
              <div className="paper-sign">— WritlynxAI</div>
              <div className="paper-seal">PROVENANCE<br /><strong>BOUND</strong></div>
            </div>
          </div>
        </div>
      </section>

      <section id="research" className="principles container">
        {principles.map(([number, title, copy]) => (
          <article className="principle" key={number}>
            <span>{number}</span><h2>{title}</h2><p>{copy}</p>
          </article>
        ))}
      </section>

      <section className="split-section container">
        <div><p className="eyebrow">THE CORE IDEA</p><h2>Generation is only one half of the problem.</h2></div>
        <p className="split-copy">
          The research layer begins after style extraction: user binding, session binding, purpose and model binding, content binding, replay resistance, revocation, isolation, and provenance are treated as first-class controls around personal style usage.
        </p>
      </section>

      <footer className="footer container">
        <span>WritlynxAI · Review II prototype</span><span>Prototype renderer · Not production security</span>
      </footer>
    </main>
  );
}
