import Link from "next/link";
import { Activity, ArrowLeft, ArrowUpRight, Zap } from "lucide-react";

export default function SiteHeader({ backHref }: { backHref?: string }) {
  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.07] bg-[rgba(6,9,20,0.84)] backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8">
        <div className="flex items-center gap-3">
          {backHref && (
            <Link
              href={backHref}
              aria-label="Go back"
              className="mr-1 rounded-lg border border-white/10 p-2 text-slate-400 transition hover:text-white"
            >
              <ArrowLeft size={16} />
            </Link>
          )}
          <Link href="/" className="flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-teal-400 text-white shadow-lg shadow-indigo-500/20">
              <Zap size={18} fill="currentColor" />
            </span>
            <span className="font-semibold tracking-tight">
              Split<span className="gradient-text">Smart</span>
            </span>
          </Link>
        </div>
        <nav className="flex items-center gap-2 text-sm sm:gap-5">
          <Link
            href="/dashboard"
            className="rounded-lg px-2 py-2 text-slate-400 transition hover:text-white"
          >
            Dashboard
          </Link>
          <Link
            href="/metrics"
            className="flex items-center gap-2 rounded-lg px-2 py-2 text-slate-400 transition hover:text-white"
          >
            <Activity size={15} />
            <span className="hidden sm:inline">System status</span>
          </Link>
          <a
            href="https://github.com/JanavGandhi/SplitSmart-AI"
            target="_blank"
            rel="noreferrer"
            aria-label="Open SplitSmart on GitHub"
            className="rounded-lg p-2 text-slate-500 transition hover:text-white"
          >
            <ArrowUpRight size={16} />
          </a>
        </nav>
      </div>
    </header>
  );
}
