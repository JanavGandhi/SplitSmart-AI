import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "SplitSmart AI — Smart Receipt Splitting & Expense Tracking",
  description:
    "Split bills instantly with Vision AI, real-time multiplayer claim rooms, and exact paise arithmetic. No login required to join a room.",
};

// ── Feature Cards Data ─────────────────────────────────────────────────────
const features = [
  {
    icon: "📸",
    title: "Zero-Typing Vision AI",
    description:
      "Snap a photo of any crumpled restaurant bill or Swiggy/Zomato order. Gemini Vision extracts every line item, tax, discount, and fee — instantly.",
    badge: "Gemini 2.5 Flash",
    color: "from-violet-500/20 to-purple-500/10",
    border: "border-violet-500/20",
  },
  {
    icon: "⚡",
    title: "No-Login Multiplayer Rooms",
    description:
      "Share a link on WhatsApp. Friends open it on their phone without signing up, enter their name, and tap items they ate in real time — everyone sees live.",
    badge: "WebSockets + Redis",
    color: "from-teal-500/20 to-cyan-500/10",
    border: "border-teal-500/20",
  },
  {
    icon: "🧮",
    title: "Exact Paise Arithmetic",
    description:
      "Zero floating-point drift. Proportional tax/GST distribution with remainder allocation. Every single paise accounted for mathematically.",
    badge: "Integer Arithmetic",
    color: "from-amber-500/20 to-yellow-500/10",
    border: "border-amber-500/20",
  },
  {
    icon: "🕸️",
    title: "Min-Cash-Flow Simplifier",
    description:
      "Graph theory debt compression reduces 11 messy IOUs into 4 optimal payments — with an interactive before/after network diagram and 1-tap UPI QR codes.",
    badge: "O(N log N) Graph",
    color: "from-rose-500/20 to-pink-500/10",
    border: "border-rose-500/20",
  },
];

// ── Tech Stack Badges ──────────────────────────────────────────────────────
const techStack = [
  "FastAPI", "Python 3.12", "PostgreSQL 16", "pgvector",
  "Redis 7", "Celery", "Next.js 15", "WebSockets",
  "Gemini Vision", "SQLAlchemy 2.0", "Alembic", "Docker",
];

// ── Stats ─────────────────────────────────────────────────────────────────
const stats = [
  { value: "0", label: "Login required to split", suffix: "" },
  { value: "₹0.01", label: "Smallest unit tracked", suffix: "" },
  { value: "11→4", label: "Payments simplified (demo)", suffix: "" },
  { value: "100%", label: "Paise conservation guarantee", suffix: "" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* ── Background Glow Effects ─────────────────────────────────────── */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden="true">
        <div
          className="absolute top-0 left-1/4 w-[600px] h-[600px] rounded-full opacity-20 blur-[120px]"
          style={{ background: "hsl(245,70%,55%)" }}
        />
        <div
          className="absolute top-1/3 right-1/4 w-[400px] h-[400px] rounded-full opacity-10 blur-[100px]"
          style={{ background: "hsl(174,72%,44%)" }}
        />
        <div
          className="absolute bottom-0 left-1/2 w-[500px] h-[300px] rounded-full opacity-10 blur-[120px]"
          style={{ background: "hsl(265,70%,50%)" }}
        />
      </div>

      {/* ── Navigation ────────────────────────────────────────────────────── */}
      <nav className="relative z-50 border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center text-lg font-bold"
              style={{ background: "linear-gradient(135deg, hsl(245,70%,55%), hsl(174,72%,44%))" }}
            >
              ⚡
            </div>
            <span className="text-lg font-bold tracking-tight">
              Split<span className="gradient-text">Smart</span> AI
            </span>
          </div>

          {/* Nav Links */}
          <div className="hidden md:flex items-center gap-6 text-sm text-[hsl(215,20%,65%)]">
            <Link href="/metrics" className="hover:text-white transition-colors">
              Live Metrics
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white transition-colors"
            >
              GitHub
            </a>
            <Link
              href="/api/docs"
              className="hover:text-white transition-colors"
            >
              API Docs
            </Link>
          </div>

          {/* CTA */}
          <Link href="/dashboard" className="btn-primary text-sm px-4 py-2">
            Open Dashboard →
          </Link>
        </div>
      </nav>

      {/* ── Hero Section ──────────────────────────────────────────────────── */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pt-24 pb-16 text-center">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-8 text-xs font-semibold"
          style={{
            background: "rgba(99,102,241,0.12)",
            border: "1px solid rgba(99,102,241,0.3)",
            color: "hsl(243,80%,75%)"
          }}
        >
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          Production-Grade Splitwise Alternative • Portfolio Demo
        </div>

        {/* Headline */}
        <h1 className="text-5xl md:text-7xl font-black tracking-tight mb-6 leading-none">
          Split Bills Like{" "}
          <span className="gradient-text">a Pro.</span>
          <br />
          <span className="text-[hsl(215,20%,55%)] font-light">No Math. No Fights.</span>
        </h1>

        {/* Subheadline */}
        <p className="text-lg md:text-xl text-[hsl(215,20%,65%)] max-w-2xl mx-auto mb-10 leading-relaxed">
          Snap a receipt. Share a link. Watch friends claim items in real time.
          AI does the math — down to the exact paise — and simplifies your debts.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
          <button
            id="launch-sandbox-btn"
            className="btn-primary text-base px-8 py-4 rounded-2xl"
            style={{ fontSize: "1rem" }}
          >
            🚀 Launch Instant Demo
            <span className="text-xs opacity-70 font-normal ml-1">(No Login)</span>
          </button>
          <Link
            href="/metrics"
            className="btn-secondary text-base px-8 py-4 rounded-2xl"
            id="view-metrics-btn"
          >
            📊 Live System Metrics
          </Link>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto mb-20">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="glass-card p-4 text-center"
            >
              <div className="text-2xl font-black gradient-text mb-1">{stat.value}</div>
              <div className="text-xs text-[hsl(215,20%,55%)]">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* ── Architecture Badge Strip ───────────────────────────────────── */}
        <div className="flex flex-wrap gap-2 justify-center mb-6">
          <p className="section-label w-full mb-2">Built with production engineering:</p>
          {techStack.map((tech) => (
            <span key={tech} className="stat-badge">
              {tech}
            </span>
          ))}
        </div>
      </section>

      {/* ── Feature Cards ────────────────────────────────────────────────── */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pb-20">
        <p className="section-label text-center mb-12">4 Core Engineering Pillars</p>
        <div className="grid md:grid-cols-2 gap-6">
          {features.map((feature, i) => (
            <div
              key={feature.title}
              className={`glass-card-hover p-8 bg-gradient-to-br ${feature.color} border ${feature.border}`}
              style={{ animationDelay: `${i * 100}ms` }}
            >
              <div className="text-4xl mb-4">{feature.icon}</div>
              <div className="flex items-start justify-between gap-4 mb-3">
                <h2 className="text-xl font-bold">{feature.title}</h2>
                <span
                  className="shrink-0 text-xs px-2.5 py-1 rounded-full font-mono font-medium"
                  style={{
                    background: "rgba(255,255,255,0.06)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    color: "hsl(215,20%,70%)"
                  }}
                >
                  {feature.badge}
                </span>
              </div>
              <p className="text-[hsl(215,20%,65%)] leading-relaxed text-sm">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How It Works ─────────────────────────────────────────────────── */}
      <section className="relative z-10 max-w-5xl mx-auto px-6 pb-24">
        <p className="section-label text-center mb-4">How It Works</p>
        <h2 className="text-3xl font-bold text-center mb-12">
          From Receipt to Settled in{" "}
          <span className="gradient-text">60 Seconds</span>
        </h2>
        <div className="relative">
          {/* Connector line */}
          <div
            className="absolute left-8 top-8 bottom-8 w-px hidden md:block"
            style={{ background: "linear-gradient(180deg, hsl(245,70%,55%), hsl(174,72%,44%))", opacity: 0.3 }}
          />
          <div className="space-y-6">
            {[
              {
                step: "01",
                title: "Upload or Snap a Receipt",
                desc: "Photo, screenshot, or PDF. Gemini Vision extracts every item automatically.",
                icon: "📸",
              },
              {
                step: "02",
                title: "Share the Room Link",
                desc: "A unique URL is generated. Friends open it on WhatsApp — no account needed.",
                icon: "🔗",
              },
              {
                step: "03",
                title: "Claim Items in Real Time",
                desc: "Everyone taps what they ate. Live avatars show who claimed what. Tax splits instantly.",
                icon: "👆",
              },
              {
                step: "04",
                title: "Simplify & Settle",
                desc: "AI compresses debts to minimum transactions. Pay with 1-tap UPI QR or deep link.",
                icon: "✅",
              },
            ].map((item) => (
              <div key={item.step} className="flex gap-6 items-start glass-card p-6">
                <div
                  className="shrink-0 w-16 h-16 rounded-2xl flex items-center justify-center text-2xl"
                  style={{
                    background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(56,189,172,0.1))",
                    border: "1px solid rgba(99,102,241,0.2)",
                  }}
                >
                  {item.icon}
                </div>
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-mono text-xs text-[hsl(245,70%,65%)] font-bold">
                      STEP {item.step}
                    </span>
                  </div>
                  <h3 className="text-lg font-semibold mb-1">{item.title}</h3>
                  <p className="text-[hsl(215,20%,60%)] text-sm">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-white/5 py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-[hsl(215,20%,55%)]">
            <span>⚡ SplitSmart AI</span>
            <span>•</span>
            <span>Production-grade portfolio project</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-[hsl(215,20%,45%)]">
            <Link href="/api/docs" className="hover:text-white transition-colors">API Docs</Link>
            <Link href="/metrics" className="hover:text-white transition-colors">Metrics</Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
