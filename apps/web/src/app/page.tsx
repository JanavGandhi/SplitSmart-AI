import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Plus, Zap } from "lucide-react";

export const metadata: Metadata = {
  title: "SplitSmart AI — Simple group expense splitting",
  description:
    "Create a group, add shared expenses, and see what everyone owes.",
};

const steps = [
  {
    number: "01",
    title: "Start a group",
    description: "Create a group for the people sharing expenses.",
  },
  {
    number: "02",
    title: "Add expenses",
    description: "Enter a bill and choose who shares it.",
  },
  {
    number: "03",
    title: "Settle up",
    description: "See balances and record payments.",
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen">
      <header className="border-b border-white/[0.07]">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Link href="/" className="flex items-center gap-3" aria-label="SplitSmart home">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-teal-400 text-white">
              <Zap size={18} fill="currentColor" />
            </span>
            <span className="font-semibold tracking-tight">SplitSmart</span>
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-300 transition hover:bg-white/[0.05] hover:text-white"
          >
            Dashboard <ArrowRight size={15} />
          </Link>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-5 pb-16 pt-20 text-center sm:px-8 sm:pt-28">
        <p className="text-sm font-medium text-indigo-300">Shared expenses, made simple</p>
        <h1 className="mt-5 text-4xl font-semibold tracking-tight text-white sm:text-6xl">
          Split bills.
          <br />
          <span className="text-indigo-300">Settle up.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-base leading-7 text-slate-400 sm:text-lg">
          Add people, enter shared expenses, and see everyone&apos;s balance update as you go.
        </p>
        <div className="mt-8 flex justify-center">
          <Link
            href="/dashboard"
            className="btn-primary justify-center px-6 py-3.5"
          >
            <Plus size={16} /> Create a group
          </Link>
        </div>
        <p className="mt-4 text-xs text-slate-500">Add people and expenses, then see who owes what.</p>
      </section>

      <section
        aria-label="How SplitSmart works"
        className="mx-auto mb-20 grid max-w-5xl gap-6 border-t border-white/[0.08] px-5 pt-8 sm:grid-cols-3 sm:px-8"
      >
        {steps.map((step) => (
          <article key={step.number} className="flex gap-4">
            <span className="pt-0.5 font-mono text-xs text-indigo-300">{step.number}</span>
            <div>
              <h2 className="text-sm font-semibold text-slate-100">{step.title}</h2>
              <p className="mt-1 text-sm leading-6 text-slate-500">{step.description}</p>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
